"""Query ChatGPT Codex usage quota from /backend-api/wham/usage."""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests

AUTH_PATH = Path.home() / ".codex" / "auth.json"
URL = "https://chatgpt.com/backend-api/wham/usage"

data = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
token = data["tokens"]["access_token"]
account_id = data["tokens"]["account_id"]

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "ChatGPT-Account-Id": account_id,
    "Origin": "https://chatgpt.com",
    "Referer": "https://chatgpt.com/",
    "User-Agent": "Mozilla/5.0",
}

resp = requests.get(URL, headers=headers, timeout=30)
resp.raise_for_status()
result = resp.json()

plan_type = result.get("plan_type", "?")
print(f"Plan: {plan_type}")
print(f"Email: {result.get('email', '?')}")
print()

rate_limit = result.get("rate_limit", result)

def fmt_dt(ts):
    if ts is None:
        return "-"
    t = int(ts)
    return datetime.fromtimestamp(t, tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")

def parse_entry(entry, label, window_label):
    used = entry.get("used_percent")
    remaining = max(0, 100 - used) if used is not None else None
    reset_at = entry.get("reset_at")
    window_sec = entry.get("limit_window_seconds", "?")
    reset_after = entry.get("reset_after_seconds")
    
    print(f"[{label}] Remaining: {remaining}%  Used: {used}%")
    print(f"    Window: {window_sec}s ({window_label})")
    print(f"    Reset at: {fmt_dt(reset_at)}  (in {reset_after}s)" if reset_after else f"    Reset at: {fmt_dt(reset_at)}")
    print()

primary = rate_limit.get("primary_window")
secondary = rate_limit.get("secondary_window")

if primary:
    parse_entry(primary, "Five Hour", "5h")
if secondary:
    parse_entry(secondary, "Weekly", "7d")

# Credits info
credits = result.get("credits", {})
if credits:
    print(f"Credits: balance={credits.get('balance')}, has_credits={credits.get('has_credits')}")
    local_msgs = credits.get("approx_local_messages", [0, 0])
    cloud_msgs = credits.get("approx_cloud_messages", [0, 0])
    print(f"    Approx local msgs: {local_msgs[0]}/{local_msgs[1]}")
    print(f"    Approx cloud msgs: {cloud_msgs[0]}/{cloud_msgs[1]}")
