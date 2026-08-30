"""FastAPI backend serving the DriveSync dashboards and JSON API."""
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import db, jobs

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "data" / "scan_cache.db")

app = FastAPI(title="DriveSync")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class DrivePathIn(BaseModel):
    label: str
    path: str


class ScanIn(BaseModel):
    label: str


class CompareIn(BaseModel):
    drive_a: str
    drive_b: str


@app.get("/", response_class=HTMLResponse)
def overview(request: Request):
    with db.connection(DB_PATH) as conn:
        drives = [dict(r) for r in db.list_drives(conn)]
        drive_paths = {d["label"]: d["path"] for d in drives}
        drives_info = {}
        for label in ("A", "B"):
            scan = db.get_latest_scan(conn, label)
            drives_info[label] = dict(scan) if scan else None
    return templates.TemplateResponse(request, "overview.html", {
        "drive_paths": drive_paths,
        "drives_json": json.dumps(drives_info),
    })


@app.get("/differences", response_class=HTMLResponse)
def differences_page(request: Request):
    with db.connection(DB_PATH) as conn:
        drives = [dict(r) for r in db.list_drives(conn)]
    return templates.TemplateResponse(request, "differences.html", {"drives": drives})


@app.get("/api/drives")
def api_list_drives():
    with db.connection(DB_PATH) as conn:
        return [dict(r) for r in db.list_drives(conn)]


@app.post("/api/drives")
def api_save_drive(payload: DrivePathIn):
    with db.connection(DB_PATH) as conn:
        db.set_drive_path(conn, payload.label, payload.path)
    return {"ok": True}


@app.post("/api/scan")
def api_scan(payload: ScanIn):
    with db.connection(DB_PATH) as conn:
        path = db.get_drive_path(conn, payload.label)
    if not path:
        raise HTTPException(400, f"No path configured for drive '{payload.label}'")
    job = jobs.start_scan_job(DB_PATH, payload.label, path)
    return {"job_id": job.id}


@app.post("/api/compare")
def api_compare(payload: CompareIn):
    job = jobs.start_compare_job(DB_PATH, payload.drive_a, payload.drive_b)
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def api_job_status(job_id: int):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return {"id": job.id, "type": job.type, "status": job.status, "progress": job.progress, "error": job.error}


@app.get("/api/summary")
def api_summary(drive_a: str, drive_b: str):
    with db.connection(DB_PATH) as conn:
        summary = db.get_comparison_summary(conn, drive_a, drive_b)
        scan_a = db.get_latest_scan(conn, drive_a)
        scan_b = db.get_latest_scan(conn, drive_b)
    return {
        "summary": summary,
        "scan_a": dict(scan_a) if scan_a else None,
        "scan_b": dict(scan_b) if scan_b else None,
    }


@app.get("/api/differences")
def api_differences(drive_a: str, drive_b: str, status: Optional[str] = None, page: int = 1, page_size: int = 100):
    offset = (page - 1) * page_size
    with db.connection(DB_PATH) as conn:
        rows = db.get_comparisons(conn, drive_a, drive_b, status=status, limit=page_size, offset=offset)
        total = db.count_comparisons(conn, drive_a, drive_b, status=status)
    return {"rows": [dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}
