"""
安全清理 token_usage_logs，强制重解析 sessions 重新计算费用。

用法:
  python scripts/reset_model_data.py          # 默认：列出数据分布 + 确认后清空
  python scripts/reset_model_data.py --all     # 跳过确认直接清空
  python scripts/reset_model_data.py --model gpt-5.5  # 只清某个型号
  python scripts/reset_model_data.py --dry-run # 仅预览，不删除
"""

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

DB_PATH = Path.home() / "AppData" / "Roaming" / "CodexUsageMonitor" / "usage.sqlite"


def main() -> None:
    parser = argparse.ArgumentParser(description="清理 token_usage_logs，强制重解析")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际删除")
    parser.add_argument("--all", action="store_true", help="跳过确认直接清空")
    parser.add_argument("--model", type=str, help="只删除指定型号 (精确匹配)")
    args = parser.parse_args()

    if not DB_PATH.is_file():
        print(f"数据库不存在: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    models = Counter(r[0] for r in conn.execute("SELECT model FROM token_usage_logs"))
    total = sum(models.values())

    if total == 0:
        print("token_usage_logs 表为空，无需清理。")
        conn.close()
        return

    print(f"数据库: {DB_PATH}")
    print(f"总记录数: {total}\n")
    print("当前型号分布:")
    for m, c in models.most_common():
        print(f"  {m:30s} {c:6d} 条")

    if args.dry_run:
        if args.model:
            n = models.get(args.model, 0)
            print(f"\n[dry-run] 将删除 model={args.model!r} 的 {n} 条记录。")
        else:
            print(f"\n[dry-run] 将删除全部 {total} 条记录。")
        conn.close()
        return

    if args.model:
        n = models.get(args.model, 0)
        if n == 0:
            print(f"\n没有 model={args.model!r} 的记录。")
            conn.close()
            return
        print(f"\n将删除 model={args.model!r} 的 {n} 条记录。")
    else:
        print(f"\n将清空全部 {total} 条记录！")

    if not args.all:
        try:
            answer = input("确认执行？(y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        if answer != "y":
            print("已取消。")
            conn.close()
            return

    if args.model:
        conn.execute("DELETE FROM token_usage_logs WHERE model=?", (args.model,))
        print(f"已删除 model={args.model!r}。")
    else:
        conn.execute("DELETE FROM token_usage_logs")
        print("已清空 token_usage_logs。")

    conn.commit()
    remaining = conn.execute("SELECT COUNT(*) FROM token_usage_logs").fetchone()[0]
    print(f"删除后剩余: {remaining} 条。")
    print("提示: 重启 app 以从头解析 sessions 文件，重新计算费用。")
    conn.close()


if __name__ == "__main__":
    main()
