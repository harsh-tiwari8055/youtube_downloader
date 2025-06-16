from fastapi import FastAPI, Request
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

class VideoURL(BaseModel):
    url: str

@app.post("/list_formats")
async def list_formats(data: VideoURL):
    url = data.url
    ydl_opts = {
        'cookiesfrombrowser': ('chrome', 'default'),  # Use Chrome browser with the default profile
        'verbose': True,                              # Enable detailed logging for debugging
    }
    formats = []

    try:
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
    except yt_dlp.utils.DownloadError as e:
        return {"error": f"Download error: {str(e)}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

    return formats

@app.post("/download_video")
async def download_video(data: dict):
    url = data["url"]
    format_id = data["format_id"]

    ydl_opts = {
        'format': format_id,
        'outtmpl': '%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        'cookiesfrombrowser': ('chrome', 'default'),  # Use Chrome browser with the default profile
        'quiet': True,                                # Suppress non-critical output
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        return {"error": f"Download error: {str(e)}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

    return {"status": "Downloaded successfully."}

@app.get("/")
def home():
    return {"message": "yt-dlp API is running"}
