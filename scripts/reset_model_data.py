"""
一次性清理：删除 default_model 的所有记录，强制从零重解析。
用法: python scripts/reset_model_data.py
"""
import sqlite3

db_path = r'C:\Users\Administrator\AppData\Roaming\CodexUsageMonitor\usage.sqlite'
conn = sqlite3.connect(db_path)

# 查看当前被错误归类的记录数
from collections import Counter
models = Counter(r[0] for r in conn.execute("SELECT model FROM token_usage_logs"))
print("Current model distribution:")
for m, c in models.most_common():
    print(f"  {m:25s} {c:6d} rows")

default_model = "gpt-4o"
wrong = conn.execute("SELECT COUNT(*) FROM token_usage_logs WHERE model=?", (default_model,)).fetchone()[0]
print(f"\nRows with model={default_model!r}: {wrong}")

if wrong > 0:
    conn.execute("DELETE FROM token_usage_logs WHERE model=?", (default_model,))
    conn.commit()
    remaining = conn.execute("SELECT COUNT(*) FROM token_usage_logs").fetchone()[0]
    print(f"Deleted. Remaining rows: {remaining}")
    print("Restart the app to re-parse all sessions with correct model names.")
else:
    print("Nothing to clean.")
conn.close()
