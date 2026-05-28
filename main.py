from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re
import httpx
from typing import Optional

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
    type: Optional[str] = "video"

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

@app.post("/download")
async def download_video(request: DownloadRequest):
    url = request.url
    platform = detect_platform(url)
    
    try:
        # يوتيوب
        if platform == 'youtube':
            ydl_opts = {'quiet': True}
            if request.type == 'audio':
                ydl_opts['format'] = 'bestaudio/best'
            else:
                ydl_opts['format'] = 'best[height<=720]'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'success': True,
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'download_url': info.get('url'),
                    'author': info.get('uploader')
                }
        
        # تيك توك
        elif platform == 'tiktok':
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://tikwm.com/api/?url={url}")
                data = resp.json()
                if data.get('code') == 0:
                    return {
                        'success': True,
                        'title': data['data'].get('title', 'TikTok'),
                        'thumbnail': data['data'].get('cover'),
                        'download_url': data['data'].get('play'),
                        'author': data['data'].get('author', {}).get('unique_id')
                    }
        
        # انستقرام
        elif platform == 'instagram':
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://instagramdl.hitesh-01.repl.co/instagram?url={url}")
                data = resp.json()
                if data.get('result'):
                    result = data['result']
                    return {
                        'success': True,
                        'title': 'Instagram',
                        'thumbnail': result.get('thumbnail'),
                        'download_url': result.get('video_url') or (result.get('images', [''])[0] if result.get('images') else None)
                    }
        
        # بينترست
        elif platform == 'pinterest':
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://pinterestdownloader.app/api/ajaxSearch?q={url}")
                data = resp.json()
                if data.get('video'):
                    return {
                        'success': True,
                        'title': 'Pinterest',
                        'thumbnail': data.get('thumbnail'),
                        'download_url': data.get('video')
                    }
        
        # تويتر
        elif platform == 'twitter':
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://twitsave.com/api/ajaxSearch",
                    data={'q': url},
                    headers={'Content-Type': 'application/x-www-form-urlencoded'})
                data = resp.json()
                if data.get('medias'):
                    for m in data['medias']:
                        if m.get('type') == 'video':
                            return {
                                'success': True,
                                'title': 'Twitter',
                                'thumbnail': data.get('thumbnail'),
                                'download_url': m.get('url')
                            }
        
        # سبوتيفاي
        elif platform == 'spotify':
            match = re.search(r'track/([a-zA-Z0-9]+)', url)
            if match:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"https://api.spotifydown.com/download/{match.group(1)}")
                    data = resp.json()
                    if data.get('link'):
                        return {
                            'success': True,
                            'title': data.get('title'),
                            'thumbnail': data.get('thumbnail'),
                            'download_url': data.get('link'),
                            'author': data.get('artist')
                        }
        
        # فيسبوك - يحتاج مفتاح API
        elif platform == 'facebook':
            return {
                'success': False,
                'error': 'فيسبوك يحتاج مفتاح API من RapidAPI'
            }
        
        # أي منصة أخرى
        else:
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'success': True,
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'download_url': info.get('url')
                }
        
        return {'success': False, 'error': 'فشل تحميل المحتوى'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.get("/")
def root():
    return {"status": "ok", "message": "Downloader API"}

@app.get("/health")
def health():
    return {"status": "healthy"}
