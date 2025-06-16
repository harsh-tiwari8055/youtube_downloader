from fastapi import FastAPI
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

class VideoURL(BaseModel):
    url: str

class FormatRequest(BaseModel):
    url: str
    format_id: str

@app.get("/")
def read_root():
    return {"message": "🎥 yt-dlp API is running."}

@app.post("/list_formats")
async def list_formats(data: VideoURL):
    url = data.url
    ydl_opts = {}
    formats = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        for f in info['formats']:
            if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none':
                resolution = f.get('format_note') or f.get('height', 'unknown')
                if str(resolution) in ['360p', '480p', '720p', '1080p']:
                    formats.append({
                        "title": info['title'],
                        "resolution": resolution,
                        "format_id": f['format_id'],
                        "ext": f['ext'],
                        "fps": f.get('fps', '')
                    })
    return formats

@app.post("/download")
async def download_video(req: VideoRequest, format_id: str):
    ydl_opts = {
        'cookiefile': 'cookies.txt',
        'format': format_id,
        'outtmpl': 'downloads/%(title)s.%(ext)s'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.download([req.url])
            return {"message": "Download started."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_stream_url")
async def get_stream_url(data: FormatRequest):
    url = data.url
    format_id = data.format_id

    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
        for f in info['formats']:
            if f['format_id'] == format_id:
                return {
                    "title": info['title'],
                    "stream_url": f['url'],
                    "ext": f['ext']
                }

    return {"error": "Format not found"}
