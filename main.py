# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

class UrlRequest(BaseModel):
    url: str
    format_id: str = None

@app.post("/list_formats")
async def list_formats(req: UrlRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="URL is required")
    ydl_opts = {"skip_download": True, "quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(req.url, download=False)
        formats = [
            {
                "format_id": fmt["format_id"],
                "resolution": fmt.get("resolution") or f"{fmt.get('width')}x{fmt.get('height')}",
                "ext": fmt["ext"],
                "filesize": fmt.get("filesize")
            }
            for fmt in info["formats"]
            if fmt.get("protocol", "").startswith(("http", "https")) and fmt.get("format_id")
        ]
    return {"title": info.get("title"), "formats": formats}

@app.post("/get_stream_url")
async def get_stream_url(req: UrlRequest):
    if not req.url or not req.format_id:
        raise HTTPException(status_code=400, detail="url and format_id are required")
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "format": req.format_id,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(req.url, download=False)
        streaming = info.get("url") or info["formats"][0].get("url")
    if not streaming:
        raise HTTPException(status_code=500, detail="No stream URL found")
    return {"title": info.get("title"), "stream_url": streaming}
