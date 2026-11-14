#!/usr/bin/env python3
from datetime import datetime, timezone
import json
import sys

def build_payload(title: str, description: str, color: int, field_name: str = "", field_value: str = "") -> str:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": "latex-vm • Poland Central"},
            "timestamp": now_iso
        }]
    }
    if field_name and field_value:
        payload["embeds"][0]["fields"] = [{
            "name": field_name,
            "value": field_value,
            "inline": False
        }]
    return json.dumps(payload)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(1)

    title = sys.argv[1]
    description = sys.argv[2]
    color = int(sys.argv[3])
    field_name = sys.argv[4] if len(sys.argv) > 4 else ""
    field_value = sys.argv[5] if len(sys.argv) > 5 else ""

    print(build_payload(title, description, color, field_name, field_value))
