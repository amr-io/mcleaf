# MCLeaf — SRE Operations & Incident Runbook

This operational runbook covers day-to-day administration, lifecycle timing baselines, incident playbooks, and disaster recovery procedures for **MCLeaf**—the self-hosted research paper collaboration platform replacing **prism.ai**.

---

## 1. Environments & Expected Timings

### 1.1 Environment Reference

| Environment | Git Branch | Azure Region | Resource Group | VM Name | Deployment Trigger |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Production** | `main` | `polandcentral` | `LATEX-SHARED` | `latex-vm` | `.github/workflows/deploy.yml` (Reviewer approval + 1m wait timer) |
| **Staging** | `dev` | `polandcentral` | `LATEX-SHARED-CLONE` | `latex-vm-clone` | `.github/workflows/deploy.yml` (Automatic on push to `dev`) |

### 1.2 Baseline Infrastructure Timings & SLOs

Use these empirically verified baseline timings to distinguish normal lifecycle progression from degraded/stuck states:

| Lifecycle Phase / Task | Typical Duration | Timeout / Alert Threshold | Where to Check |
| :--- | :--- | :--- | :--- |
| **Azure VM Start API (`POST /start`)** | $15\text{--}25\text{ s}$ | $> 60\text{ s}$ | Azure Portal / `worker.js` |
| **Stage 1: Kernel Boot $\rightarrow$ Docker Up (`25%`)** | $25\text{--}35\text{ s}$ | $> 60\text{ s}$ | `/dev/shm/boot-status.json` |
| **Stage 2: MongoDB 6.0 Ready (`50%`)** | $40\text{--}55\text{ s}$ | $> 90\text{ s}$ | `/dev/shm/boot-status.json` |
| **Stage 3: Overleaf Runit Services Up (`75%`)** | $65\text{--}85\text{ s}$ | $> 120\text{ s}$ | `/dev/shm/boot-status.json` |
| **Stage 4: Cold Boot Complete (`HTTP 200`, `100%`)** | $105\text{--}120\text{ s}$ | $> 180\text{ s}$ | `/dev/shm/boot-status.json` |
| **Warm Container Restart (`docker restart sharelatex`)** | $15\text{--}30\text{ s}$ | $> 60\text{ s}$ | `curl -I http://127.0.0.1:8000/login` |
| **Scheduled R2 Backup (`backup-overleaf.sh`)** | $15\text{--}45\text{ s}$ | $> 180\text{ s}$ | `journalctl -u latex-backup.service` |
| **Disaster Recovery (`restore-overleaf.sh`)** | $45\text{--}180\text{ s}$ | $> 300\text{ s}$ | `~/backups/restore.log` |
| **Idle Shutdown Window (6 $\times$ 5m checks)** | $30\text{ min}$ | N/A | `journalctl -u overleaf-idle-check.service` |

---

## 2. Standard Operating Procedures (SOPs)

### SOP-01: Waking the VM Manually from CLI

If you need to work on a deallocated VM without opening the web UI in a browser:

```bash
# 1. Start the VM (swap in LATEX-SHARED-CLONE / latex-vm-clone for staging)
az vm start --resource-group LATEX-SHARED --name latex-vm --no-wait

# 2. Check power state until it reports 'VM running'
az vm get-instance-view --resource-group LATEX-SHARED --name latex-vm \
  --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv

# 3. SSH in and watch the boot tracker hit 100%
ssh azureuser@<VM_PUBLIC_IP> "watch -n 2 'cat /dev/shm/boot-status.json; echo; systemctl status overleaf-boot-tracker.service --no-pager -n 5'"
```

### SOP-02: Pausing Auto-Shutdown for Maintenance

`overleaf-idle-check.timer` runs every $5\text{ minutes}$. While an active SSH session (`who`) normally keeps the VM awake, if you plan to run detached background jobs (`nohup` / `tmux` with no attached client) that don't generate HTTP traffic or `pdflatex` processes, pause the timer first:

```bash
# Pause the idle-shutdown timer
sudo systemctl stop overleaf-idle-check.timer
sudo systemctl stop overleaf-idle-check.service

# Confirm the timer is stopped
systemctl list-timers overleaf-idle-check.timer

# --- Run your maintenance tasks here ---

# Re-enable automatic scale-to-zero when finished
sudo systemctl start overleaf-idle-check.timer
```

### SOP-03: Running a Manual R2 Backup Before Changes

Before upgrading Overleaf, editing toolkit configs, or touching MongoDB collections, trigger a fresh backup to Cloudflare R2:

```bash
# 1. Run the backup service
sudo systemctl start latex-backup.service

# 2. Check the logs to confirm rclone uploaded the archive cleanly
sudo journalctl -u latex-backup.service -n 50 --no-pager

# 3. Confirm exit status 0
systemctl show latex-backup.service -p Result,ExecMainStatus
```

### SOP-04: Upgrading Overleaf CE or the TeX Live Container

`versions.yml` is the single source of truth for runtime and container versions. Do not update the Dockerfile or Ansible role defaults directly for a normal image upgrade.

1. **Create a Separate Version-Bump PR:** On `dev`, update the relevant value in `versions.yml`:

   ```yaml
   overleaf_version: "<new-version>"
   overleaf_image_suffix: "with-texlive-full"
   overleaf_toolkit_ref: "<compatible-toolkit-ref>"
   mongo_version: "<compatible-mongo-version>"
   redis_version: "<compatible-redis-version>"
   ```

   Change only the fields required for the upgrade. The image tag is derived as `<overleaf_version>-<overleaf_image_suffix>`, while Ansible uses `overleaf_toolkit_ref` to check out the toolkit and `overleaf_image_tag` to select the running container.

2. **Validate the Pull Request:** Let CI run the Terraform, Ansible, build, and Trivy checks. A pull request does not deploy to staging.

3. **Build and Deploy to Staging:** Merge or push the version-bump PR to `dev`. The CI/CD workflow builds or reuses `ghcr.io/amr-io/sharelatex:<overleaf_version>-<overleaf_image_suffix>`, scans it with Trivy, and then deploys to `LATEX-SHARED-CLONE`.

   Before changing an existing deployment, the Overleaf Ansible role starts `latex-backup.service` when the current `config/version` differs from the new image tag. Confirm the result and run the manual pre-change backup from **SOP-03** if you need an on-demand snapshot.

4. **Verify Staging:** Check the running image and application health:

   ```bash
   sudo docker inspect --format '{{.Config.Image}}' sharelatex
   curl -I http://127.0.0.1:8000/login
   ```

   From the staging host, confirm the login page returns `HTTP 200` or `302`, open a project, and test a small LaTeX compile. The Ansible role independently fails if the running image differs from `overleaf_image_tag` or if the web service does not become responsive.

5. **Promote to Production:** Open a PR from `dev` to `main` only after staging is verified. Merge it after review and approval; the production deployment requires the GitHub Actions production environment approval.

**Rollback**

- **Before promotion:** Close or revert the version-bump PR on `dev`, then confirm the staging deployment is back at the previous image and passes `/login` plus a sample compile.
- **After promotion:** Revert `versions.yml` to the last known-good values in a new PR on `dev`, merge it, and let the normal build-backup-deploy-verify pipeline return staging to that version.
- If the reverted release fails or data compatibility is uncertain, restore a pre-upgrade R2 or local backup using the **Disaster Recovery** procedures in this runbook. Do not restore data while the application is running.

### SOP-05: Creating Overleaf Users or Admins

Public sign-ups are disabled. To invite a new researcher or grant admin rights:

```bash
sudo docker exec sharelatex /bin/bash -ce "cd /var/www/overleaf && node /var/www/overleaf/server-ce/cron/create-user.js --admin --email=researcher@example.com"
```
Copy the activation link printed in the terminal and send it to the user.

---

## 3. Incident Response Playbooks

### PLAYBOOK-01: Cold Boot Hangs Below `100%` or Returns `502 Bad Gateway`

**Symptoms:** The Cloudflare wakeup page stays stuck at `25%`, `50%`, or `75%` for more than 3 minutes, or Nginx serves a `502`.

**How to Fix:**

1. **Check the boot status file and service logs:**
   ```bash
   cat /dev/shm/boot-status.json
   sudo journalctl -u overleaf-boot-tracker.service -n 100 --no-pager
   ```

2. **Stuck at `25%` (Docker or `/datadisk` mount problem):**
   - Check if `/datadisk` (`/dev/sdb`) is mounted:
     ```bash
     df -h /datadisk
     sudo dmesg -T | grep -E "sdb|ext4"
     ```
   - If `/datadisk` isn't mounted, run `sudo mount -a` and restart Docker and the tracker:
     ```bash
     sudo systemctl restart docker overleaf-boot-tracker.service
     ```

3. **Stuck at `50%` (MongoDB failing to start):**
   - Check `sudo docker logs mongo --tail 100`.
   - If MongoDB crashed uncleanly or has a corrupted lock file, jump to **PLAYBOOK-04**.

4. **Stuck at `75%` (Overleaf web worker inside `sharelatex` isn't answering on port `8000`):**
   - Check the internal Runit services inside the container:
     ```bash
     sudo docker exec sharelatex sv status /etc/service/*
     sudo docker logs sharelatex --tail 100
     ```
   - Restart the internal web service and re-run the boot tracker:
     ```bash
     sudo docker exec sharelatex sv restart /etc/service/web
     sudo systemctl restart overleaf-boot-tracker.service
     ```

### PLAYBOOK-02: VM Deallocated While someone Was Reading a Document

**Symptoms:** A user left a tab open reading a PDF without typing or compiling for $> 30\text{ minutes}$, and the VM went to sleep.

**How to Fix:**

1. **Wake the VM:** Refresh the browser tab (which triggers `worker.js`) or run **SOP-01**.
2. **Check what triggered the shutdown:**
   ```bash
   sudo journalctl -u overleaf-idle-check.service -n 100 --no-pager
   ```
3. **Verify the loopback `iptables` counter rule exists:**
   `idle-deallocate.sh` watches traffic hitting `127.0.0.1:8000`. Make sure a firewall reload didn't wipe the counter rule:
   ```bash
   sudo iptables -L -v -n -x | grep 8000
   ```
   If the rule is missing, re-run the `daemons` Ansible role or restart `overleaf-idle-check.service`.

### PLAYBOOK-03: Compile Timeouts, High Swap Usage, or OOM Kills

**Symptoms:** Heavy TikZ/PGFPlots documents time out during compilation, or the host feels sluggish.

**How to Fix:**

1. **Check RAM, `zram` compression, and swap usage:**
   ```bash
   free -h
   zramctl
   swapon --show
   ```
   *What you want to see:* `/dev/zram0` (`lz4`) listed with a higher priority than `/datadisk/swapfile` ($8\text{ GB}$).
2. **Check kernel `sysctl` settings:**
   ```bash
   sysctl vm.swappiness vm.overcommit_memory vm.vfs_cache_pressure
   ```
   *Expected values:* `vm.swappiness = 100`, `vm.overcommit_memory = 1`, `vm.vfs_cache_pressure = 50`. Reload with `sudo sysctl --system` if needed.
3. **Kill runaway `pdflatex` loops:**
   If a broken LaTeX macro is pegging both vCPUs at 100%:
   ```bash
   ps aux | grep -E "pdflatex|xelatex|lualatex"
   sudo docker exec sharelatex pkill -9 -f pdflatex
   ```

### PLAYBOOK-04: Redis Snapshot Errors or MongoDB Corruption

**Symptoms:** Saving edits fails, logging in throws `500 Internal Server Error`, or the `mongo` container keeps restarting.

**How to Fix:**

1. **Redis `BGSAVE` Errors:**
   - Check `sudo docker logs redis --tail 50`.
   - Confirm `vm.overcommit_memory = 1` is set on the host (`sudo sysctl -w vm.overcommit_memory=1`).
2. **MongoDB WiredTiger Repair:**
   - Try a WiredTiger repair first:
     ```bash
     sudo docker stop sharelatex
     sudo docker run --rm -v /datadisk/overleaf/data/mongo:/data/db mongo:6.0 mongod --repair --dbpath /data/db
     sudo chown -R 999:999 /datadisk/overleaf/data/mongo
     sudo docker start mongo sharelatex
     ```
   - If the repair doesn't bring `mongo` back cleanly, run **Section 4: Disaster Recovery (DR)** to restore from the latest R2 backup.

### PLAYBOOK-05: Fail2Ban Blocked a Legitimate User (`nginx-limit-req`)

**Symptoms:** A researcher on university Wi-Fi (shared campus NAT) gets connection timeouts or `429` errors while others can access the site fine.

**How to Fix:**

1. **List banned IPs in the `nginx-limit-req` jail:**
   ```bash
   sudo fail2ban-client status nginx-limit-req
   ```
2. **Unban the IP:**
   ```bash
   sudo fail2ban-client set nginx-limit-req unbanip <RESEARCHER_IP>
   ```
3. **Loosen the rate limit if it keeps happening:** Adjust the burst settings in `ansible/roles/nginx/templates/overleaf.j2` and `nginx-limit-req.jail.local.j2` and deploy via GitHub Actions.

---

## 4. Disaster Recovery (DR) Execution Guide

MCLeaf's `restore-overleaf.sh` script can restore the entire stack either from **Cloudflare R2** (via `rclone`) or from the local backup directory (`~/backups`) if R2 is unreachable.

### Option A: One-Click Restore via GitHub Actions (Recommended)

1. Open the GitHub repository $\rightarrow$ **Actions** $\rightarrow$ **`Disaster Recovery (Restore Overleaf)`** (`.github/workflows/recovery.yml`).
2. Click **Run workflow**.
3. Pick the environment (`production` or `staging`) and optionally enter a specific `overleaf-backup-<timestamp>.tar.gz` filename (leave blank to automatically grab the newest backup).
4. Watch the workflow run. It SSHes into the VM, runs `restore-overleaf.sh`, waits for `http://127.0.0.1:8000/login` to return `HTTP 200`, and posts a completion embed to Discord.

### Option B: Manual CLI Restore (`restore-overleaf.sh`)

If you already have an SSH session on the VM (or GitHub Actions is down), run the script directly:

```bash
# 1. SSH into the host and pause the idle-shutdown timer while restoring
ssh azureuser@<VM_PUBLIC_IP>
sudo systemctl stop overleaf-idle-check.timer

# 2a. Restore the newest backup available (checks R2 first, then ~/backups/)
sudo /usr/local/bin/restore-overleaf.sh

# 2b. OR pass a specific backup filename to restore a known point in time
sudo /usr/local/bin/restore-overleaf.sh overleaf-backup-2026-11-15_12-00-00.tar.gz

# 3. Follow the restore log in real time (if running in another terminal)
tail -f ~/backups/restore.log

# 4. Re-enable the idle-shutdown timer once healthy
sudo systemctl start overleaf-idle-check.timer
```

### What `restore-overleaf.sh` Does Step-by-Step

1. **Loads Secrets & Sets Traps:** Sources `/etc/overleaf-secrets.env`. Any unexpected failure triggers `trap 'on_error ${LINENO}' ERR`, which logs the exact failing line number and exit code to `~/backups/restore.log` (`${BACKUP_DIR}/restore.log`) and fires an `"emergency"` Discord alert.
2. **Resolves the Backup Archive (3-Tier Fallback):**
   - Uses `$1` if you passed a filename on the command line.
   - Otherwise queries Cloudflare R2 (`rclone lsf --sort time --reverse`) for the newest `overleaf-backup-*.tar.gz`.
   - If R2 returns nothing (or is unreachable), falls back to the newest `overleaf-backup-*.tar.gz` already sitting in `${BACKUP_DIR}`.
3. **Downloads & Verifies Checksums:**
   - Creates a temporary staging directory `${BACKUP_DIR}/temp_restore_<timestamp>` (automatically cleaned up on script exit).
   - If the chosen archive isn't already in `${BACKUP_DIR}`, downloads it from R2 using `rclone copy --retries 3`.
   - Verifies outer tarball integrity with `tar -tzf`, extracts it into the temp folder, and confirms both `mongo_dump.archive.gz` and `overleaf_data.tar.gz` are present inside.
4. **Stops Overleaf & Restores Data:**
   - Stops `sharelatex` (`docker stop sharelatex`) and makes sure `mongo` is running.
   - Restores MongoDB cleanly via `docker exec -i mongo mongorestore --archive --gzip --drop < mongo_dump.archive.gz`.
   - Unpacks `overleaf_data.tar.gz` (`--overwrite --same-owner`) into `${TOOLKIT_DIR}/data`.
   - If `overleaf_config.tar.gz` is included in the bundle, extracts it into `${TOOLKIT_DIR}` and resets `${TOOLKIT_DIR}/config` ownership to the Ansible user.
5. **Verifies Health on Port `8000`:**
   - Starts `sharelatex` and polls `curl -s -f -o /dev/null http://127.0.0.1:8000/login` every $2\text{ s}$ for up to 30 attempts ($60\text{ s}$).
   - Once `/login` returns `HTTP 200`, logs the total time taken and sends a `"success"` Discord alert. If it times out, sends an `"emergency"` Discord alert with the last 8 lines of `docker logs sharelatex`.

---

## 5. Quick Diagnostic Reference

| What You Need | Path / Unit | Command |
| :--- | :--- | :--- |
| **Boot Progress JSON** | `/dev/shm/boot-status.json` | `cat /dev/shm/boot-status.json \| jq .` |
| **Boot Tracker Logs** | `overleaf-boot-tracker.service` | `sudo journalctl -u overleaf-boot-tracker.service -f` |
| **Idle Deallocator Logs** | `overleaf-idle-check.service` | `sudo journalctl -u overleaf-idle-check.service -n 50` |
| **R2 Backup Logs** | `latex-backup.service` | `sudo journalctl -u latex-backup.service -n 50` |
| **Disaster Recovery Log** | `~/backups/restore.log` | `tail -n 100 ~/backups/restore.log` |
| **Host Secrets File** | `/etc/overleaf-secrets.env` | `sudo ls -la /etc/overleaf-secrets.env` (Should be `0600`) |
| **Local Loopback Health** | `http://127.0.0.1:8000/login` | `curl -I http://127.0.0.1:8000/login` |
| **Overleaf Container Logs** | `sharelatex` container | `sudo docker logs sharelatex --tail 100 -f` |
| **Nginx Logs** | `/var/log/nginx/` | `sudo tail -f /var/log/nginx/error.log /var/log/nginx/access.log` |
| **Fail2Ban Jail Status** | `nginx-limit-req` | `sudo fail2ban-client status nginx-limit-req` |
| **Swap & ZRAM Status** | `/dev/zram0`, `/datadisk/swapfile` | `zramctl && swapon --show && free -h` |
