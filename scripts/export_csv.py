from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config
from app.storage.db import get_connection
from app.storage.migrations import run_migrations
from app.storage.repository import Repository


def main():
    config = load_config()
    conn = get_connection(config.paths.db_path)
    run_migrations(conn)
    repo = Repository(conn)

    rows = repo.get_token_usage(limit=100000)
    if not rows:
        print("No data to export.")
        return

    out_path = Path("codex_token_usage_export.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "event_time", "session_id", "model",
            "input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens",
            "estimated_cost_usd",
        ])
        for r in rows:
            writer.writerow([
                r["event_time"], r["session_id"], r["model"],
                r["input_tokens"], r["output_tokens"], r["cached_input_tokens"], r["reasoning_tokens"],
                r["estimated_cost_usd"],
            ])

    total_tokens = sum(
        r["input_tokens"] + r["output_tokens"] + r["cached_input_tokens"] + r["reasoning_tokens"]
        for r in rows
    )
    total_cost = sum(r["estimated_cost_usd"] or 0 for r in rows)
    print(f"Exported {len(rows)} entries to {out_path}")
    print(f"Total tokens: {total_tokens:,}, Total cost: ${total_cost:.6f}")


if __name__ == "__main__":
    main()
