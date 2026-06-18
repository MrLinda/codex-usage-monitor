from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL：并发读写不阻塞
    conn.execute("PRAGMA journal_mode=WAL")
    # WAL 下 NORMAL 已足够安全且远比 FULL 少 fsync
    conn.execute("PRAGMA synchronous=NORMAL")
    # 临时表 / 排序走内存
    conn.execute("PRAGMA temp_store=MEMORY")
    # 20MB 页缓存（负数代表 KB）
    conn.execute("PRAGMA cache_size=-20000")
    # 128MB mmap，加速读热点
    conn.execute("PRAGMA mmap_size=134217728")
    # 多线程访问时遇到锁，最多等 5 秒再报错
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
