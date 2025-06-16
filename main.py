from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

class VideoRequest(BaseModel):
    url: str

@app.post("/list_formats")
async def list_formats(req: VideoRequest):
    ydl_opts = {
        'cookiefile': 'cookies.txt',  # Path to exported cookies
        'quiet': True,
        'skip_download': True,
        'forcejson': True,
        'simulate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(req.url, download=False)
            formats = info_dict.get("formats", [])
            filtered = [
                {
                    "format_id": fmt.get("format_id"),
                    "ext": fmt.get("ext"),
                    "resolution": fmt.get("format_note"),
                    "filesize": fmt.get("filesize"),
                    "url": fmt.get("url")
                }
                for fmt in formats
                if fmt.get("vcodec") != "none"  # only video formats
            ]
            return {"title": info_dict.get("title"), "formats": filtered}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
