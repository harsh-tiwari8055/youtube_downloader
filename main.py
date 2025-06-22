import os
import uuid
import subprocess
import signal
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from yt_dlp import YoutubeDL

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COOKIES_FILE = os.path.join(os.getcwd(), "youtube_cookies.txt")

# Download state memory: {track_id: {...}}
download_tasks = {}


class DownloadRequest(BaseModel):
    url: str
    format_id: str


def get_total_bytes(url, format_id):
    try:
        ydl_opts = {
            "cookiefile": COOKIES_FILE,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "extract_flat": False,
            "forcejson": True,
            "socket_timeout": 30,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            for f in info.get("formats", []):
                if str(f.get("format_id")) == str(format_id):
                    return f.get("filesize") or f.get("filesize_approx") or 0
    except Exception as e:
        print("Metadata extraction error:", e)
    return 0


@app.post("/start_download")
def start_download(data: DownloadRequest):
    track_id = str(uuid.uuid4())
    filename_template = f"{track_id}.%(ext)s"
    output_template = os.path.join(DOWNLOAD_DIR, filename_template)

    # Get expected filesize
    total_bytes = get_total_bytes(data.url, data.format_id)

    cmd = [
        "yt-dlp",
        "--cookies", COOKIES_FILE,
        "-f", data.format_id,
        "-o", output_template,
        data.url
    ]

    process = subprocess.Popen(cmd)

    download_tasks[track_id] = {
        "pid": process.pid,
        "url": data.url,
        "format_id": data.format_id,
        "status": "downloading",
        "output_template": output_template,
        "filename_prefix": track_id,
        "total_bytes": total_bytes
    }

    return {"track_id": track_id, "message": "Download started"}


@app.post("/pause/{track_id}")
def pause_download(track_id: str):
    task = download_tasks.get(track_id)
    if not task:
        return JSONResponse(content={"error": "Invalid track_id"}, status_code=404)

    try:
        os.kill(task["pid"], signal.SIGTERM)
        task["status"] = "paused"
        return {"message": f"Download {track_id} paused."}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/resume/{track_id}")
def resume_download(track_id: str):
    task = download_tasks.get(track_id)
    if not task:
        return JSONResponse(content={"error": "Invalid track_id"}, status_code=404)

    cmd = [
        "yt-dlp",
        "--cookies", COOKIES_FILE,
        "-f", task["format_id"],
        "-o", task["output_template"],
        task["url"]
    ]

    process = subprocess.Popen(cmd)
    task["pid"] = process.pid
    task["status"] = "downloading"

    return {"message": f"Resumed download {track_id}."}


@app.post("/cancel/{track_id}")
def cancel_download(track_id: str):
    task = download_tasks.get(track_id)
    if not task:
        return JSONResponse(content={"error": "Invalid track_id"}, status_code=404)

    try:
        os.kill(task["pid"], signal.SIGTERM)
    except Exception:
        pass

    # Delete all files matching the track_id prefix
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(track_id):
            os.remove(os.path.join(DOWNLOAD_DIR, f))

    download_tasks.pop(track_id, None)
    return {"message": f"Download {track_id} canceled and cleaned up."}


@app.get("/status/{track_id}")
def get_status(track_id: str):
    task = download_tasks.get(track_id)
    if not task:
        return JSONResponse(content={"error": "Invalid track_id"}, status_code=404)

    # Try to estimate current progress
    total = task.get("total_bytes", 0)
    current = 0
    percent = None
    part_file = None

    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(task["filename_prefix"]) and f.endswith(".part"):
            part_file = os.path.join(DOWNLOAD_DIR, f)
            break

    if part_file and os.path.exists(part_file):
        current = os.path.getsize(part_file)
        if total > 0:
            percent = round((current / total) * 100, 2)

    task_status = {
        "status": task.get("status", "unknown"),
        "current_bytes": current,
        "total_bytes": total,
        "percent": percent
    }

    return task_status
