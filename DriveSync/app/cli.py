"""Command-line entry point for testing a scan without the web UI.

Usage:
    python -m app.cli scan --drive A --path D:\\ --db data/scan_cache.db
"""
import argparse

from . import db
from .comparator import compare_drives
from .scanner import scan_drive


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan a drive and cache file metadata in SQLite.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a directory and store results.")
    scan_parser.add_argument("--drive", required=True, help="Label for this drive, e.g. A or B.")
    scan_parser.add_argument("--path", required=True, help="Root path to scan, e.g. D:\\")
    scan_parser.add_argument("--db", default="data/scan_cache.db", help="Path to the SQLite cache file.")

    compare_parser = subparsers.add_parser("compare", help="Compare two previously scanned drives.")
    compare_parser.add_argument("--drive-a", required=True, help="Label of the first drive, e.g. A.")
    compare_parser.add_argument("--drive-b", required=True, help="Label of the second drive, e.g. B.")
    compare_parser.add_argument("--db", default="data/scan_cache.db", help="Path to the SQLite cache file.")

    args = parser.parse_args()

    if args.command == "scan":
        with db.connection(args.db) as conn:
            def report(stats):
                print(f"\r  scanned {stats.file_count} files, {stats.total_size / (1024**3):.2f} GB, "
                      f"{stats.skipped_count} skipped", end="", flush=True)

            print(f"Scanning drive '{args.drive}' at '{args.path}'...")
            stats = scan_drive(conn, args.drive, args.path, progress_callback=report)
            print()
            print(f"Done in {stats.elapsed_seconds:.1f}s: {stats.file_count} files, "
                  f"{stats.total_size / (1024**3):.2f} GB, {stats.skipped_count} skipped.")

    elif args.command == "compare":
        with db.connection(args.db) as conn:
            def report(stats):
                print(f"\r  only_a={stats.only_a} only_b={stats.only_b} identical={stats.identical} "
                      f"same_content={stats.same_content} conflict={stats.conflict} error={stats.error} "
                      f"(hashed {stats.hashed_count})", end="", flush=True)

            print(f"Comparing '{args.drive_a}' vs '{args.drive_b}'...")
            stats = compare_drives(conn, args.drive_a, args.drive_b, progress_callback=report)
            print()
            print(f"Only on {args.drive_a}: {stats.only_a}")
            print(f"Only on {args.drive_b}: {stats.only_b}")
            print(f"Identical: {stats.identical}")
            print(f"Same content, different metadata: {stats.same_content}")
            print(f"Conflicts (content differs on both sides): {stats.conflict}")
            print(f"Errors: {stats.error}")
            print(f"Files hashed this run: {stats.hashed_count}")


if __name__ == "__main__":
    main()

