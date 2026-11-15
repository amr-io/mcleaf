#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD_HELPER="${SCRIPT_DIR}/helpers/discord_payload.py"

# Load env vars
ENV_FILE="/etc/overleaf-secrets.env"
if [ -f "${ENV_FILE}" ]; then
    # Use sudo if running as non-root
    if [ "$(id -u)" -eq 0 ]; then
        source "${ENV_FILE}"
    else
        DISCORD_WEBHOOK_URL=$(sudo grep '^DISCORD_WEBHOOK_URL=' "${ENV_FILE}" | cut -d'"' -f2)
    fi
fi

if [ -z "${DISCORD_WEBHOOK_URL}" ]; then
    echo "[notify-discord] WARNING: DISCORD_WEBHOOK_URL not configured. Skipping alert." >&2
    exit 0
fi

# Function to send an embedded dc msg
# Usage: send_discord_embed "STATUS_TYPE" "TITLE" "DESCRIPTION" [EXTRA_FIELD_NAME] [EXTRA_FIELD_VALUE]
send_discord_embed() {
    local status_type="$1"
    local title="$2"
    local description="$3"
    local field_name="${4:-}"
    local field_value="${5:-}"

    local color=3447003 # Default Blue

    case "${status_type}" in
        "success"|"shutdown")
            color=3066993 # Emerald Green
            ;;
        "warning")
            color=15844367 # Amber
            ;;
        "error"|"emergency")
            color=15158332 # Crimson Red
            ;;
    esac

    # Build JSON payload using python helper
    local payload
    payload=$(python3 "${PAYLOAD_HELPER}" "${title}" "${description}" "${color}" "${field_name}" "${field_value}")

    curl -s -o /dev/null \
        -H "Content-Type: application/json" \
        -X POST -d "${payload}" \
        "${DISCORD_WEBHOOK_URL}" > /dev/null 2>&1 || true
}

# If executed from the terminal
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [ "$#" -lt 3 ]; then
        echo "Usage: $0 <success|warning|error|shutdown> <title> <description> [field_name] [field_value]"
        exit 1
    fi
    send_discord_embed "$@"
fi
