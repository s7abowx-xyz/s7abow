from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re
import httpx
from typing import Optional

app = FastAPI(title="Downloader API", description="API لتحميل من جميع المنصات")

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
    type: Optional[str] = "video"

class InfoRequest(BaseModel):
    url: str

# ============== دوال مساعدة ==============

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

def extract_instagram_id(url: str) -> Optional[str]:
    patterns = [
        r'instagram\.com\/p\/([^/?]+)',
        r'instagram\.com\/reel\/([^/?]+)',
        r'instagram\.com\/tv\/([^/?]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def detect_platform(url: str) -> str:
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'tiktok.com' in url_lower:
        return 'tiktok'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
        return 'facebook'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif 'spotify.com' in url_lower:
        return 'spotify'
    elif 'pinterest.com' in url_lower:
        return 'pinterest'
    else:
        return 'other'

# ============== معالجات المنصات ==============

async def handle_youtube(url: str, media_type: str):
    if media_type == 'audio':
        ydl_opts = {'format': 'bestaudio/best', 'quiet': True}
    else:
        ydl_opts = {'format': 'best[height<=720]', 'quiet': True}
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'success': True,
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'download_url': info.get('url'),
            'author': info.get('uploader'),
            'duration': info.get('duration')
        }

async def handle_tiktok(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://tikwm.com/api/?url={url}")
        data = response.json()
        if data.get('code') == 0:
            return {
                'success': True,
                'title': data['data'].get('title', 'TikTok Video'),
                'thumbnail': data['data'].get('cover'),
                'download_url': data['data'].get('play'),
                'author': data['data'].get('author', {}).get('unique_id')
            }
    return {'success': False, 'error': 'فشل تحميل تيك توك'}

async def handle_instagram(url: str):
    # استخدام API مجاني لانستقرام
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://instagramdl.hitesh-01.repl.co/instagram?url={url}")
        data = response.json()
        if data.get('result'):
            result = data['result']
            return {
                'success': True,
                'title': 'Instagram Post',
                'thumbnail': result.get('thumbnail'),
                'download_url': result.get('video_url') or (result.get('images', [''])[0] if result.get('images') else None),
                'type': 'video' if result.get('video_url') else 'image'
            }
    return {'success': False, 'error': 'فشل تحميل انستقرام'}

async def handle_facebook(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://getvideo.p.rapidapi.com/?url={url}", 
            headers={'X-RapidAPI-Key': 'YOUR_KEY'})  # تحتاج مفتاح API
        # أو استخدام خدمة بديلة
        return {'success': False, 'error': 'فيسبوك - ستحتاج مفتاح API'}

async def handle_twitter(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.post("https://twitsave.com/api/ajaxSearch",
            data={'q': url},
            headers={'Content-Type': 'application/x-www-form-urlencoded'})
        data = response.json()
        if data.get('medias'):
            video = next((m for m in data['medias'] if m.get('type') == 'video'), None)
            if video:
                return {
                    'success': True,
                    'title': 'Twitter Video',
                    'thumbnail': data.get('thumbnail'),
                    'download_url': video.get('url')
                }
    return {'success': False, 'error': 'فشل تحميل تويتر'}

async def handle_spotify(url: str):
    track_id = re.search(r'track/([a-zA-Z0-9]+)', url)
    if track_id:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.spotifydown.com/download/{track_id.group(1)}")
            data = response.json()
            if data.get('link'):
                return {
                    'success': True,
                    'title': data.get('title'),
                    'thumbnail': data.get('thumbnail'),
                    'download_url': data.get('link'),
                    'author': data.get('artist')
                }
    return {'success': False, 'error': 'فشل تحميل سبوتيفاي'}

async def handle_pinterest(url: str):
    pin_id = re.search(r'pin/(\d+)', url)
    if pin_id:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://pinterestdownloader.app/api/ajaxSearch?q={url}")
            data = response.json()
            if data.get('video'):
                return {
                    'success': True,
                    'title': 'Pinterest Video',
                    'thumbnail': data.get('thumbnail'),
                    'download_url': data.get('video')
                }
    return {'success': False, 'error': 'فشل تحميل بينترست'}

# ============== الـ Endpoints ==============

@app.get("/")
def root():
    return {"message": "Downloader API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/info")
async def video_info(request: InfoRequest):
    platform = detect_platform(request.url)
    try:
        if platform == 'youtube':
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(request.url, download=False)
                return {'success': True, 'title': info.get('title'), 'thumbnail': info.get('thumbnail')}
        else:
            return {'success': True, 'title': 'محتوى', 'thumbnail': None}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
async def download_video(request: DownloadRequest):
    platform = detect_platform(request.url)
    
    try:
        if platform == 'youtube':
            result = await handle_youtube(request.url, request.type)
        elif platform == 'tiktok':
            result = await handle_tiktok(request.url)
        elif platform == 'instagram':
            result = await handle_instagram(request.url)
        elif platform == 'pinterest':
            result = await handle_pinterest(request.url)
        elif platform == 'twitter':
            result = await handle_twitter(request.url)
        elif platform == 'spotify':
            result = await handle_spotify(request.url)
        elif platform == 'facebook':
            result = await handle_facebook(request.url)
        else:
            # محاولة استخدام yt-dlp لأي منصة أخرى
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(request.url, download=False)
                result = {
                    'success': True,
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'download_url': info.get('url')
                }
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
