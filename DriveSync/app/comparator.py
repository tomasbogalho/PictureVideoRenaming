"""Builds a diff between two scanned drives, hashing only files whose size/mtime differ."""
import os
import sqlite3
from dataclasses import dataclass
from typing import Callable, Optional

from . import db
from .hasher import compute_sha256

STATUS_ONLY_A = "only_a"
STATUS_ONLY_B = "only_b"
STATUS_IDENTICAL = "identical"
STATUS_SAME_CONTENT = "same_content"  # metadata differs but bytes are identical
STATUS_CONFLICT = "conflict"
STATUS_ERROR = "error"  # file vanished or became unreadable since the scan


@dataclass
class CompareStats:
    only_a: int = 0
    only_b: int = 0
    identical: int = 0
    same_content: int = 0
    conflict: int = 0
    error: int = 0
    hashed_count: int = 0


ProgressCallback = Callable[[CompareStats], None]


def _ensure_hash(conn: sqlite3.Connection, drive: str, root: str, rel_path: str, row) -> str:
    if row["hash"] is not None and row["hash_size"] == row["size"] and row["hash_mtime"] == row["mtime"]:
        return row["hash"]
    full_path = os.path.join(root, rel_path.replace("/", os.sep))
    file_hash = compute_sha256(full_path)
    db.set_hash(conn, drive, rel_path, file_hash, row["size"], row["mtime"])
    return file_hash


def compare_drives(
    conn: sqlite3.Connection,
    drive_a: str,
    drive_b: str,
    progress_callback: Optional[ProgressCallback] = None,
    progress_interval: int = 200,
) -> CompareStats:
    root_a = db.get_latest_root(conn, drive_a)
    root_b = db.get_latest_root(conn, drive_b)
    if root_a is None:
        raise ValueError(f"No scan found for drive '{drive_a}'. Run a scan first.")
    if root_b is None:
        raise ValueError(f"No scan found for drive '{drive_b}'. Run a scan first.")

    rows_a = db.get_files_by_path(conn, drive_a)
    rows_b = db.get_files_by_path(conn, drive_b)

    stats = CompareStats()
    results = []
    all_paths = sorted(set(rows_a) | set(rows_b))

    for i, rel_path in enumerate(all_paths, start=1):
        a = rows_a.get(rel_path)
        b = rows_b.get(rel_path)

        if b is None:
            stats.only_a += 1
            results.append((rel_path, STATUS_ONLY_A, a["size"], None, a["mtime"], None, None, None))
        elif a is None:
            stats.only_b += 1
            results.append((rel_path, STATUS_ONLY_B, None, b["size"], None, b["mtime"], None, None))
        elif a["size"] == b["size"] and a["mtime"] == b["mtime"]:
            stats.identical += 1
            results.append((rel_path, STATUS_IDENTICAL, a["size"], b["size"], a["mtime"], b["mtime"], a["hash"], b["hash"]))
        else:
            try:
                hash_a = _ensure_hash(conn, drive_a, root_a, rel_path, a)
                hash_b = _ensure_hash(conn, drive_b, root_b, rel_path, b)
                stats.hashed_count += 1
            except OSError as e:
                print(f"Could not hash '{rel_path}': {e}")
                stats.error += 1
                results.append((rel_path, STATUS_ERROR, a["size"], b["size"], a["mtime"], b["mtime"], None, None))
                continue

            if hash_a == hash_b:
                stats.same_content += 1
                results.append((rel_path, STATUS_SAME_CONTENT, a["size"], b["size"], a["mtime"], b["mtime"], hash_a, hash_b))
            else:
                stats.conflict += 1
                results.append((rel_path, STATUS_CONFLICT, a["size"], b["size"], a["mtime"], b["mtime"], hash_a, hash_b))

        if progress_callback and i % progress_interval == 0:
            progress_callback(stats)

    db.replace_comparisons(conn, drive_a, drive_b, results)

    if progress_callback:
        progress_callback(stats)

    return stats
