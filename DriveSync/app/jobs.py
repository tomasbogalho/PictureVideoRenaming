"""In-memory background job tracking for long-running scans/compares.

A local single-user app doesn't need a task queue: a thread per job plus a
dict polled over HTTP is enough, and keeps the dependency list small.
"""
import threading
import traceback
from dataclasses import dataclass, field, asdict
from typing import Optional

from . import db
from .scanner import scan_drive
from .comparator import compare_drives

_jobs: dict[int, "Job"] = {}
_jobs_lock = threading.Lock()
_next_id = 0


@dataclass
class Job:
    id: int
    type: str
    status: str = "running"  # running | done | error
    progress: dict = field(default_factory=dict)
    error: Optional[str] = None


def _new_job(job_type: str) -> Job:
    global _next_id
    with _jobs_lock:
        _next_id += 1
        job = Job(id=_next_id, type=job_type)
        _jobs[job.id] = job
    return job


def get_job(job_id: int) -> Optional[Job]:
    return _jobs.get(job_id)


def start_scan_job(db_path: str, drive: str, path: str) -> Job:
    job = _new_job("scan")

    def run():
        try:
            with db.connection(db_path) as conn:
                job.progress = asdict(scan_drive(conn, drive, path, progress_callback=lambda s: _update(job, s)))
                job.status = "done"
        except Exception as e:
            job.error = str(e)
            job.status = "error"
            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
    return job


def start_compare_job(db_path: str, drive_a: str, drive_b: str) -> Job:
    job = _new_job("compare")

    def run():
        try:
            with db.connection(db_path) as conn:
                job.progress = asdict(compare_drives(conn, drive_a, drive_b, progress_callback=lambda s: _update(job, s)))
                job.status = "done"
        except Exception as e:
            job.error = str(e)
            job.status = "error"
            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
    return job


def _update(job: Job, stats) -> None:
    job.progress = asdict(stats)
