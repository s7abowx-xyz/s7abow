from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re

app = FastAPI(title="Downloader API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DownloadRequest(BaseModel):
    url: str

def extract_direct_url(url: str):
    """استخراج رابط التحميل المباشر من أي منصة"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # الحصول على أفضل رابط
        if 'url' in info:
            video_url = info['url']
        elif 'formats' in info and len(info['formats']) > 0:
            video_url = info['formats'][-1]['url']
        else:
            video_url = None
        
        return {
            'title': info.get('title', 'Unknown'),
            'thumbnail': info.get('thumbnail', ''),
            'download_url': video_url,
            'duration': info.get('duration', 0),
            'author': info.get('uploader', 'Unknown')
        }

@app.post("/download")
async def download(request: DownloadRequest):
    try:
        result = extract_direct_url(request.url)
        return {
            'success': True,
            'data': result
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Downloader API - يدعم جميع المنصات",
        "platforms": ["YouTube", "TikTok", "Instagram", "Facebook", "Twitter", "Pinterest", "Spotify", "Vimeo", "Twitch", "SoundCloud"]
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
