"""SQLite schema and data access for the drive scan cache."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    drive TEXT NOT NULL,
    rel_path TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    hash TEXT,
    hash_size INTEGER,
    hash_mtime REAL,
    seen INTEGER NOT NULL DEFAULT 1,
    UNIQUE(drive, rel_path)
);
CREATE INDEX IF NOT EXISTS idx_files_drive_relpath ON files(drive, rel_path);

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY,
    drive TEXT NOT NULL,
    root_path TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    file_count INTEGER NOT NULL DEFAULT 0,
    total_size INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS comparisons (
    id INTEGER PRIMARY KEY,
    drive_a TEXT NOT NULL,
    drive_b TEXT NOT NULL,
    rel_path TEXT NOT NULL,
    status TEXT NOT NULL,
    size_a INTEGER,
    size_b INTEGER,
    mtime_a REAL,
    mtime_b REAL,
    hash_a TEXT,
    hash_b TEXT,
    compared_at TEXT NOT NULL,
    UNIQUE(drive_a, drive_b, rel_path)
);
CREATE INDEX IF NOT EXISTS idx_comparisons_pair_status ON comparisons(drive_a, drive_b, status);

CREATE TABLE IF NOT EXISTS drives (
    label TEXT PRIMARY KEY,
    path TEXT NOT NULL
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def connection(db_path: str):
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def start_scan(conn: sqlite3.Connection, drive: str, root_path: str) -> int:
    cur = conn.execute(
        "INSERT INTO scans (drive, root_path, started_at) VALUES (?, ?, datetime('now'))",
        (drive, root_path),
    )
    conn.commit()
    return cur.lastrowid


def finish_scan(conn: sqlite3.Connection, scan_id: int, file_count: int, total_size: int, skipped_count: int) -> None:
    conn.execute(
        """UPDATE scans SET finished_at = datetime('now'), file_count = ?, total_size = ?,
           skipped_count = ?, status = 'completed' WHERE id = ?""",
        (file_count, total_size, skipped_count, scan_id),
    )
    conn.commit()


def fail_scan(conn: sqlite3.Connection, scan_id: int) -> None:
    conn.execute("UPDATE scans SET finished_at = datetime('now'), status = 'error' WHERE id = ?", (scan_id,))
    conn.commit()


def clear_seen_flags(conn: sqlite3.Connection, drive: str) -> None:
    conn.execute("UPDATE files SET seen = 0 WHERE drive = ?", (drive,))


def upsert_file(conn: sqlite3.Connection, drive: str, rel_path: str, size: int, mtime: float) -> None:
    """Insert or update a file row. Clears the cached hash if size/mtime changed."""
    existing = conn.execute(
        "SELECT size, mtime, hash, hash_size, hash_mtime FROM files WHERE drive = ? AND rel_path = ?",
        (drive, rel_path),
    ).fetchone()

    if existing is None:
        conn.execute(
            "INSERT INTO files (drive, rel_path, size, mtime, seen) VALUES (?, ?, ?, ?, 1)",
            (drive, rel_path, size, mtime),
        )
        return

    hash_still_valid = existing["hash"] is not None and existing["hash_size"] == size and existing["hash_mtime"] == mtime
    if hash_still_valid:
        conn.execute(
            "UPDATE files SET size = ?, mtime = ?, seen = 1 WHERE drive = ? AND rel_path = ?",
            (size, mtime, drive, rel_path),
        )
    else:
        conn.execute(
            """UPDATE files SET size = ?, mtime = ?, hash = NULL, hash_size = NULL, hash_mtime = NULL, seen = 1
               WHERE drive = ? AND rel_path = ?""",
            (size, mtime, drive, rel_path),
        )


def remove_unseen(conn: sqlite3.Connection, drive: str) -> int:
    """Delete rows for files that were not encountered in the latest scan (i.e. removed from disk)."""
    cur = conn.execute("DELETE FROM files WHERE drive = ? AND seen = 0", (drive,))
    return cur.rowcount


def set_hash(conn: sqlite3.Connection, drive: str, rel_path: str, file_hash: str, size: int, mtime: float) -> None:
    conn.execute(
        "UPDATE files SET hash = ?, hash_size = ?, hash_mtime = ? WHERE drive = ? AND rel_path = ?",
        (file_hash, size, mtime, drive, rel_path),
    )


def get_latest_root(conn: sqlite3.Connection, drive: str) -> str | None:
    row = conn.execute(
        "SELECT root_path FROM scans WHERE drive = ? ORDER BY id DESC LIMIT 1", (drive,)
    ).fetchone()
    return row["root_path"] if row else None


def get_files_by_path(conn: sqlite3.Connection, drive: str) -> dict:
    rows = conn.execute(
        "SELECT rel_path, size, mtime, hash, hash_size, hash_mtime FROM files WHERE drive = ?", (drive,)
    ).fetchall()
    return {row["rel_path"]: row for row in rows}


def replace_comparisons(conn: sqlite3.Connection, drive_a: str, drive_b: str, rows: list) -> None:
    """Replace all comparison rows for a drive pair with a freshly computed set."""
    conn.execute("DELETE FROM comparisons WHERE drive_a = ? AND drive_b = ?", (drive_a, drive_b))
    conn.executemany(
        """INSERT INTO comparisons
           (drive_a, drive_b, rel_path, status, size_a, size_b, mtime_a, mtime_b, hash_a, hash_b, compared_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        [(drive_a, drive_b, *row) for row in rows],
    )
    conn.commit()


def get_comparison_summary(conn: sqlite3.Connection, drive_a: str, drive_b: str) -> dict:
    rows = conn.execute(
        "SELECT status, COUNT(*) AS count FROM comparisons WHERE drive_a = ? AND drive_b = ? GROUP BY status",
        (drive_a, drive_b),
    ).fetchall()
    return {row["status"]: row["count"] for row in rows}


def get_comparisons(conn: sqlite3.Connection, drive_a: str, drive_b: str, status: str | None = None,
                     limit: int = 200, offset: int = 0) -> list:
    if status:
        return conn.execute(
            """SELECT * FROM comparisons WHERE drive_a = ? AND drive_b = ? AND status = ?
               ORDER BY rel_path LIMIT ? OFFSET ?""",
            (drive_a, drive_b, status, limit, offset),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM comparisons WHERE drive_a = ? AND drive_b = ? ORDER BY rel_path LIMIT ? OFFSET ?",
        (drive_a, drive_b, limit, offset),
    ).fetchall()


def count_comparisons(conn: sqlite3.Connection, drive_a: str, drive_b: str, status: str | None = None) -> int:
    if status:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM comparisons WHERE drive_a = ? AND drive_b = ? AND status = ?",
            (drive_a, drive_b, status),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM comparisons WHERE drive_a = ? AND drive_b = ?", (drive_a, drive_b)
        ).fetchone()
    return row["c"]


def set_drive_path(conn: sqlite3.Connection, label: str, path: str) -> None:
    conn.execute("INSERT OR REPLACE INTO drives (label, path) VALUES (?, ?)", (label, path))
    conn.commit()


def get_drive_path(conn: sqlite3.Connection, label: str) -> str | None:
    row = conn.execute("SELECT path FROM drives WHERE label = ?", (label,)).fetchone()
    return row["path"] if row else None


def list_drives(conn: sqlite3.Connection) -> list:
    return conn.execute("SELECT label, path FROM drives ORDER BY label").fetchall()


def get_latest_scan(conn: sqlite3.Connection, drive: str):
    return conn.execute(
        "SELECT * FROM scans WHERE drive = ? ORDER BY id DESC LIMIT 1", (drive,)
    ).fetchone()
