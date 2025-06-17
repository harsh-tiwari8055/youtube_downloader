from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from yt_dlp import YoutubeDL
import os

app = FastAPI()

COOKIES_FILE = os.path.join(os.getcwd(), "youtube_cookies.txt")

@app.get("/")
def read_root():
    return {"status": "YouTube Downloader API is running."}


@app.post("/list_formats")
async def list_formats(request: Request):
    data = await request.json()
    url = data.get("url")

    ydl_opts = {
        "cookiefile": COOKIES_FILE,
        "quiet": True,
        "skip_download": True,
        "forcejson": True,
        "extract_flat": False,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_duration = info.get("duration", 0)
            formats = []

            for f in info.get("formats", []):
                filesize = f.get("filesize")
                if not filesize and video_duration and f.get("tbr"):
                    filesize = (f["tbr"] * 1000 / 8) * video_duration

                formats.append({
                    "format_id": f["format_id"],
                    "ext": f["ext"],
                    "resolution": f.get("resolution") or f"{f.get('height', '?')}p",
                    "filesize": f"{filesize / (1024 * 1024):.2f} MB" if filesize else "Unknown",
                    "format_note": f.get("format_note"),
                    "vcodec": f.get("vcodec"),
                    "acodec": f.get("acodec"),
                })

            return JSONResponse(content={"title": info.get("title"), "formats": formats})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


class StreamRequest(BaseModel):
    url: str
    format_id: str


@app.post("/get_stream_url")
async def get_stream_url(data: StreamRequest):
    ydl_opts = {
        "cookiefile": COOKIES_FILE,
        "quiet": True,
        "skip_download": True,
        "format": data.format_id,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(data.url, download=False)
            selected_format = next(
                (f for f in info.get("formats", []) if str(f.get("format_id")) == str(data.format_id)), None
            )

            if not selected_format:
                return JSONResponse(content={"error": "Format not found"}, status_code=404)

            return {
                "stream_url": selected_format.get("url"),
                "title": info.get("title", "video"),
                "ext": selected_format.get("ext", "mp4")
            }

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
