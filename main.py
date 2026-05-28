from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp
import re
from typing import Optional, Dict
import json

app = FastAPI(title="Downloader API", description="API لتحميل من جميع المنصات")

# CORS عشان الموقع الثاني يقدر يستخدم الـ API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# نماذج البيانات
class DownloadRequest(BaseModel):
    url: str
    type: Optional[str] = "video"  # video أو audio

class InfoRequest(BaseModel):
    url: str

# دالة تحديد المنصة
def detect_platform(url: str) -> str:
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'tiktok.com' in url:
        return 'tiktok'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'facebook.com' in url or 'fb.com' in url:
        return 'facebook'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    elif 'spotify.com' in url:
        return 'spotify'
    elif 'pinterest.com' in url:
        return 'pinterest'
    else:
        return 'other'

# دالة استخراج ID يوتيوب
def extract_youtube_id(url: str) -> Optional[str]:
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([^&]+)',
        r'(?:youtu\.be\/)([^?]+)',
        r'(?:youtube\.com\/embed\/)([^/?]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# دالة جلب المعلومات
def get_video_info(url: str, download_type: str = 'video'):
    platform = detect_platform(url)
    
    if platform == 'youtube':
        if download_type == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
            }
        else:
            ydl_opts = {
                'format': 'best[height<=720]',
                'quiet': True,
                'no_warnings': True,
            }
    else:
        # للمنصات الأخرى
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'success': True,
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'platform': platform,
                'formats': len(info.get('formats', [])),
                'url': info.get('url'),
                'audio_url': next((f.get('url') for f in info.get('formats', []) if f.get('acodec') != 'none' and f.get('vcodec') == 'none'), None)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

# ============== الـ Endpoints ==============

@app.get("/")
def root():
    return {
        "message": "🎥 Downloader API - مرحباً!",
        "endpoints": {
            "POST /download": "تحميل فيديو/صوت",
            "POST /info": "جلب معلومات الفيديو",
            "GET /health": "فحص صحة الـ API"
        }
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/info")
async def video_info(request: InfoRequest):
    """جلب معلومات الفيديو بدون تحميل"""
    result = get_video_info(request.url, 'video')
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'فشل جلب المعلومات'))
    return JSONResponse(content=result)

@app.post("/download")
async def download_video(request: DownloadRequest):
    """الحصول على رابط التحميل المباشر"""
    platform = detect_platform(request.url)
    
    try:
        # ليوتيوب - استخدام مباشر
        if platform == 'youtube':
            video_id = extract_youtube_id(request.url)
            if not video_id:
                raise HTTPException(status_code=400, detail="رابط يوتيوب غير صالح")
            
            if request.type == 'audio':
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                }
            else:
                ydl_opts = {
                    'format': 'best[height<=720]',
                    'quiet': True,
                }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(request.url, download=False)
                download_url = info.get('url')
                
                return JSONResponse(content={
                    'success': True,
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'download_url': download_url,
                    'platform': platform,
                    'type': request.type,
                    'duration': info.get('duration'),
                    'author': info.get('uploader')
                })
        
        # لتيك توك
        elif platform == 'tiktok':
            response = await fetch_url(f"https://tikwm.com/api/?url={request.url}")
            data = response.json()
            if data.get('code') == 0:
                return JSONResponse(content={
                    'success': True,
                    'title': data['data'].get('title'),
                    'thumbnail': data['data'].get('cover'),
                    'download_url': data['data'].get('play'),
                    'platform': platform,
                    'type': request.type
                })
        
        # لانستقرام وفيسبوك وتويتر
        elif platform in ['instagram', 'facebook', 'twitter']:
            # استخدام خدمة خارجية شاملة
            response = await fetch_url(f"https://api.genshindev.xyz/api/downloader?url={request.url}")
            data = response.json()
            if data.get('status') == 200:
                return JSONResponse(content={
                    'success': True,
                    'title': data.get('title', 'محتوى'),
                    'thumbnail': data.get('thumbnail'),
                    'download_url': data.get('url') or data.get('video_url'),
                    'platform': platform,
                    'type': request.type
                })
        
        # للسبوتيفاي
        elif platform == 'spotify':
            response = await fetch_url(f"https://api.spotifydown.com/download/{extract_spotify_id(request.url)}")
            data = response.json()
            if data.get('link'):
                return JSONResponse(content={
                    'success': True,
                    'title': data.get('title'),
                    'thumbnail': data.get('thumbnail'),
                    'download_url': data.get('link'),
                    'platform': platform,
                    'type': 'audio'
                })
        
        # استخدام yt-dlp لأي منصة أخرى
        else:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(request.url, download=False)
                return JSONResponse(content={
                    'success': True,
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'download_url': info.get('url'),
                    'platform': platform,
                    'type': request.type
                })
        
        raise HTTPException(status_code=404, detail="فشل تحميل المحتوى")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# دوال مساعدة
import httpx
async def fetch_url(url: str):
    async with httpx.AsyncClient() as client:
        return await client.get(url)

def extract_spotify_id(url: str) -> Optional[str]:
    match = re.search(r'track/([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)