"""Chunked file hashing so large files never need to be loaded into memory whole."""
import hashlib

CHUNK_SIZE = 1024 * 1024  # 1 MiB


def compute_sha256(file_path: str) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()
