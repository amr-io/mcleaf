import urllib.request
from datetime import datetime, timezone
import json
import argparse
import os

COLORS = {
    "success": 3066993,  # Green
    "info": 3447003,  # Blue
    "warning": 15844367,  # Amber
    "error": 15158332,  # Red
}


def send_embed(title, description, type, url, fields, footer, webhook_url):
    if not webhook_url:
        print("::warning::No Discord webhook URL provided; skipping notif.")
        return
    embed = {
        "title": title,
        "description": description,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "color": COLORS.get(type, COLORS["info"]),
        "footer": {"text": footer},
        "author": {
            "name": "MCLeaf Notification System",
            "url": "https://github.com/amr-io/mcleaf",
            "icon_url": "https://icons.iconarchive.com/icons/academicons-team/academicons/512/overleaf-icon.png",
        },
    }
    if url:
        embed["url"] = url
    if fields:
        embed["fields"] = fields

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps({"embeds": [embed]}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "mcleaf-version-check",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        print(f"Discord webhook responded with HTTP {response.status}")


def _parse_field(raw, inline):
    if "=" not in raw:
        raise argparse.ArgumentTypeError(f"Incorrect Field Declaration!")
    name, value = raw.split("=", 1)
    return {"name": name.strip(), "value": value.strip(), "inline": inline}


def main():
    parser = argparse.ArgumentParser(description="Send a webhook embed notification")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--type", choices=COLORS.keys(), default="info")
    parser.add_argument("--url")
    parser.add_argument("--field", action="append", default=[])
    parser.add_argument("--inline-field", action="append", default=[])
    parser.add_argument("--footer", default="MCLeaf • CI/CD")
    args = parser.parse_args()

    fields = [_parse_field(f, inline=True) for f in args.inline_field] + [
        _parse_field(f, inline=False) for f in args.field
    ]
    send_embed(
        title=args.title,
        description=args.description,
        type=args.type,
        fields=fields,
        url=args.url,
        footer=args.footer,
        webhook_url=os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    )


if __name__ == "__main__":
    main()
