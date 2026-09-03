# Picture and Video Renaming Tools

A collection of local Python tools for organizing media files and comparing storage drives.

## Features

- Rename pictures and videos from their embedded capture date, with filesystem dates as a fallback.
- Preview renames before changing any files.
- Find matching `.jpg` and `.jpeg` files and delete only byte-identical duplicates.
- Report filenames that do not contain a selected year.
- Scan and compare two drives through the DriveSync web dashboard or command line.

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux for the media utilities
- Windows is recommended for the current drive-oriented examples

## Installation

Clone the repository and install the media-tool dependencies:

```powershell
git clone https://github.com/tomasbogalho/PictureVideoRenaming.git
cd PictureVideoRenaming
python -m pip install -r requirements.txt
```

To use DriveSync, install its additional dependencies:

```powershell
python -m pip install -r DriveSync/requirements.txt
```

## Media Renamer

Run the interactive script:

```powershell
python script.py
```

Enter the directory to process, then choose a mode:

- `validate` previews the proposed names without changing files.
- `rename` applies the changes.

Supported image formats are JPG, JPEG, PNG, GIF, and BMP. Supported video formats are MP4, AVI, MOV, MKV, and FLV. Name collisions receive a numeric suffix such as `_01`. Results are written to `rename_log.txt`.

Always run `validate` and review the log before using `rename`.

## JPEG Duplicate Cleaner

This tool finds `.jpg` and `.jpeg` files with the same base name in each directory. It compares their sizes and SHA-256 hashes before considering the `.jpeg` copy safe to remove.

```powershell
python jpegdelete.py
```

- `validate` reports files that would be deleted.
- `delete` removes only identical `.jpeg` copies.

Results are written to `jpeg_delete_log.txt`.

## Filename Validator

Generate a report of files whose names do not contain a selected four-digit year:

```powershell
python validator.py
```

The report is written to `file_info.txt`.

## DriveSync

DriveSync is a local FastAPI dashboard for scanning and comparing two drives. It caches file metadata in SQLite and hashes files only when comparison requires it.

Start the dashboard:

```powershell
cd DriveSync
python run.py
```

The app opens at `http://127.0.0.1:8000`. Configure drive A and drive B, scan both, then compare them to review files that are unique, identical, metadata-only matches, conflicting, or unreadable.

DriveSync currently provides scanning and comparison only. It does not copy, overwrite, or delete files.

### DriveSync CLI

From the `DriveSync` directory:

```powershell
python -m app.cli scan --drive A --path "D:\" --db data/scan_cache.db
python -m app.cli scan --drive B --path "E:\" --db data/scan_cache.db
python -m app.cli compare --drive-a A --drive-b B --db data/scan_cache.db
```

## Generated Files

The scripts create or update local output files in the current working directory:

- `rename_log.txt`
- `jpeg_delete_log.txt`
- `file_info.txt`
- `DriveSync/data/scan_cache.db`

Review these files before rerunning a tool because text reports and logs are overwritten on each run.