"""Recursive directory scanner that populates the SQLite metadata cache.

Uses a manual stack (not os.walk) so we can skip junctions/symlinks explicitly
and keep memory usage flat regardless of folder depth.
"""
import os
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import db

DEFAULT_IGNORE_NAMES = {
    "System Volume Information",
    "$RECYCLE.BIN",
    "Thumbs.db",
    "desktop.ini",
    ".DS_Store",
}


@dataclass
class ScanStats:
    file_count: int = 0
    total_size: int = 0
    skipped_count: int = 0
    elapsed_seconds: float = 0.0


ProgressCallback = Callable[[ScanStats], None]


def _relpath(root: str, full_path: str) -> str:
    rel = os.path.relpath(full_path, root)
    return rel.replace(os.sep, "/")


def scan_drive(
    conn: sqlite3.Connection,
    drive: str,
    root_path: str,
    ignore_names: Optional[set] = None,
    progress_callback: Optional[ProgressCallback] = None,
    progress_interval: int = 500,
) -> ScanStats:
    """Walk root_path, upserting every file's metadata into the DB for the given drive label."""
    if not os.path.isdir(root_path):
        raise ValueError(f"Path does not exist or is not a directory: {root_path}")

    ignore_names = ignore_names or DEFAULT_IGNORE_NAMES
    stats = ScanStats()
    start = time.monotonic()

    scan_id = db.start_scan(conn, drive, root_path)
    db.clear_seen_flags(conn, drive)

    try:
        stack = [root_path]
        while stack:
            current_dir = stack.pop()
            try:
                entries = list(os.scandir(current_dir))
            except (PermissionError, OSError) as e:
                print(f"Skipping unreadable directory '{current_dir}': {e}")
                stats.skipped_count += 1
                continue

            for entry in entries:
                if entry.name in ignore_names:
                    continue
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue

                    file_stat = entry.stat(follow_symlinks=False)
                    rel_path = _relpath(root_path, entry.path)
                    db.upsert_file(conn, drive, rel_path, file_stat.st_size, file_stat.st_mtime)
                    stats.file_count += 1
                    stats.total_size += file_stat.st_size
                except (PermissionError, OSError) as e:
                    print(f"Skipping unreadable file '{entry.path}': {e}")
                    stats.skipped_count += 1
                    continue

            if progress_callback and stats.file_count % progress_interval == 0:
                progress_callback(stats)

        db.remove_unseen(conn, drive)
        conn.commit()
        stats.elapsed_seconds = time.monotonic() - start
        db.finish_scan(conn, scan_id, stats.file_count, stats.total_size, stats.skipped_count)
    except Exception:
        db.fail_scan(conn, scan_id)
        raise

    if progress_callback:
        progress_callback(stats)

    return stats
