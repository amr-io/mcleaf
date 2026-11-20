import json, os, re, sys, urllib.request
from pathlib import Path
from datetime import datetime, timezone

DOCKER_HUB_URL = "https://hub.docker.com/v2/namespaces/sharelatex/repositories/sharelatex/tags?page_size=100"
SEMVER = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)$"
)  # Search for semantic versioning (e.g. 6.3.4)
parse = lambda v: tuple(
    map(int, SEMVER.match(v).groups())
)  # Parse semantic versioning into a tuple of integers


def get_latest_stable() -> str:
    req = urllib.request.Request(
        DOCKER_HUB_URL, headers={"User-Agent": "mcleaf-version-check"}
    )
    tags = [
        r["name"] for r in json.load(urllib.request.urlopen(req, timeout=10))["results"]
    ]
    stable = [t for t in tags if SEMVER.match(t)]
    return max(stable, key=parse)


def read_version_from_yml(versions_yml: Path) -> str:
    for line in versions_yml.read_text().splitlines():
        match = re.match(r'^overleaf_version:\s*["\']?([^"\'#\s]+)', line.strip())
        if match:
            return match.group(1)
    raise RuntimeError(f"Could not find Overleaf version in {versions_yml}")


def classify_bump(cur: tuple[int, int, int], lat: tuple[int, int, int]) -> str:
    if lat <= cur:
        return "none"
    if lat[0] > cur[0]:
        return "MAJOR"
    if lat[1] > cur[1]:
        return "MINOR"
    return "PATCH"


def send_discord_notif(webhook_url, current, latest, bump, trigger):
    is_major = bump == "MAJOR"
    color = 15844367 if is_major else 3447003  # Amber for MAJOR, Blue otherwise
    note = None
    if is_major:
        note = "**Major release:** Check MongoDB, Redis, Tex Live, and Overleaf Toolkit compatibility before bumping `versions.yml`."
    else:
        note = "Update `overleaf_version` in `versions.yml` to the latest version."

    payload = {
        "embeds": [
            {
                "title": f"Overleaf CE Update Available! ({bump})",
                "description": f"A newer stable Overleaf CE release is available on Docker Hub.\n\n{note}",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "color": color,
                "footer": {
                    "text": (
                        f"MCLeaf • {trigger.capitalize()} Version Check!"
                        if trigger
                        else "MCLeaf • Version Check!"
                    )
                },
                "fields": [
                    {
                        "name": "Current Version",
                        "value": f"`{current}`",
                        "inline": True,
                    },
                    {
                        "name": "Available Stable Release",
                        "value": f"`{latest}`",
                        "inline": True,
                    },
                    {
                        "name": "Release Notes",
                        "value": f"[Overleaf Wiki](https://docs.overleaf.com/on-premises/release-notes/release-notes-{parse(latest)[0]}.x.x)",
                        "inline": False,
                    },
                ],
                "author": {
                    "name": "MCLeaf Notification System",
                    "url": "https://github.com/amr-io/mcleaf",
                    "icon_url": "https://icons.iconarchive.com/icons/academicons-team/academicons/512/overleaf-icon.png",
                },
            }
        ]
    }

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "mcleaf-version-check",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        print(f"Discord webhook responded with HTTP {response.status}")


def main():
    trigger = sys.argv[2] if len(sys.argv) > 2 else None
    versions_yml = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("versions.yml")
    current = read_version_from_yml(versions_yml)
    latest = get_latest_stable()
    cur, lat = parse(current), parse(latest)
    bump = classify_bump(cur, lat)

    print(f"Current: {current} | Latest: {latest} | Bump: {bump}")

    if bump == "none":
        print("Already up to date.")
        return

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("::warning::No Discord webhook URL provided; skipping notif.")
        return

    send_discord_notif(webhook_url, current, latest, bump, trigger)


if __name__ == "__main__":
    main()
