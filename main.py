from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse
from yt_dlp import YoutubeDL
import os

app = FastAPI()

# Define path to your cookies file
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
        "extract_flat": False
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [
                {
                    "format_id": f["format_id"],
                    "ext": f["ext"],
                    "resolution": f.get("resolution") or f"{f.get('height', '?')}p",
                    "filesize": f.get("filesize"),
                    "format_note": f.get("format_note")
                }
                for f in info.get("formats", [])
                if f.get("vcodec") != "none" and f.get("acodec") != "none"
            ]
        return JSONResponse(content={"title": info.get("title"), "formats": formats})
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/download")
async def download_video(url: str = Form(...), format_id: str = Form(...)):
    output_file = "%(title)s.%(ext)s"
    
    ydl_opts = {
        "cookies": COOKIES_FILE,
        "format": format_id,
        "outtmpl": output_file
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return {"status": "Download successful!"}
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
