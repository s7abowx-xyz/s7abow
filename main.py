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
        # ========== يوتيوب ==========
        if platform == 'youtube':
            if request.type == 'audio':
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
                    'author': info.get('uploader')
                }
        
        # ========== تيك توك ==========
        elif platform == 'tiktok':
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://tikwm.com/api/?url={url}")
                data = resp.json()
                if data.get('code') == 0:
                    return {
                        'success': True,
                        'title': data['data'].get('title'),
                        'thumbnail': data['data'].get('cover'),
                        'download_url': data['data'].get('play'),
                        'author': data['data'].get('author', {}).get('unique_id')
                    }
        
        # ========== انستقرام ==========
        elif platform == 'instagram':
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://instagramdl.hitesh-01.repl.co/instagram?url={url}")
                data = resp.json()
                if data.get('result'):
                    result = data['result']
                    return {
                        'success': True,
                        'title': 'Instagram Post',
                        'thumbnail': result.get('thumbnail'),
                        'download_url': result.get('video_url') or (result.get('images', [''])[0] if result.get('images') else None)
                    }
        
        # ========== فيسبوك ==========
        elif platform == 'facebook':
            async with httpx.AsyncClient() as client:
                try:
                    ydl_opts = {'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        return {
                            'success': True,
                            'title': info.get('title'),
                            'thumbnail': info.get('thumbnail'),
                            'download_url': info.get('url')
                        }
                except:
                    return {'success': False, 'error': 'فشل تحميل فيسبوك'}
        
        # ========== تويتر ==========
        elif platform == 'twitter':
            async with httpx.AsyncClient() as client:
                try:
                    ydl_opts = {'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        return {
                            'success': True,
                            'title': info.get('title'),
                            'thumbnail': info.get('thumbnail'),
                            'download_url': info.get('url')
                        }
                except:
                    return {'success': False, 'error': 'فشل تحميل تويتر'}
        
        # ========== سبوتيفاي - API جديد شغال ==========
        elif platform == 'spotify':
            async with httpx.AsyncClient() as client:
                # استخراج ID الأغنية
                track_match = re.search(r'track/([a-zA-Z0-9]+)', url)
                if not track_match:
                    return {'success': False, 'error': 'رابط سبوتيفاي غير صالح'}
                
                track_id = track_match.group(1)
                
                # استخدام API سبوتيفاي شغال
                api_url = f"https://spotify-downloader.com/api/download?url={url}"
                
                try:
                    resp = await client.get(api_url, timeout=20)
                    data = resp.json()
                    
                    if data.get('downloadUrl'):
                        return {
                            'success': True,
                            'title': data.get('track', data.get('title', 'Spotify Track')),
                            'thumbnail': data.get('image', data.get('thumbnail')),
                            'download_url': data.get('downloadUrl'),
                            'author': data.get('artist')
                        }
                except:
                    pass
                
                # API بديل
                api_url2 = f"https://api.spotifydown.com/download/{track_id}"
                try:
                    resp = await client.get(api_url2, timeout=20)
                    data = resp.json()
                    
                    if data.get('link'):
                        return {
                            'success': True,
                            'title': data.get('title'),
                            'thumbnail': data.get('thumbnail'),
                            'download_url': data.get('link'),
                            'author': data.get('artist')
                        }
                except:
                    pass
                
                return {'success': False, 'error': 'فشل تحميل سبوتيفاي - حاول رابط آخر'}
        
        # ========== بينترست - API جديد شغال ==========
        elif platform == 'pinterest':
            async with httpx.AsyncClient() as client:
                # استخراج ID الصورة
                pin_match = re.search(r'pin/(\d+)', url)
                if not pin_match:
                    return {'success': False, 'error': 'رابط بينترست غير صالح'}
                
                pin_id = pin_match.group(1)
                
                # استخدام API بينترست شغال
                api_url = f"https://pinterestdownloader.app/api/ajaxSearch?q={url}"
                
                try:
                    resp = await client.get(api_url, timeout=15)
                    data = resp.json()
                    
                    if data.get('video'):
                        return {
                            'success': True,
                            'title': 'Pinterest Video',
                            'thumbnail': data.get('thumbnail'),
                            'download_url': data.get('video')
                        }
                    elif data.get('images') and len(data['images']) > 0:
                        return {
                            'success': True,
                            'title': 'Pinterest Image',
                            'thumbnail': data.get('thumbnail', data['images'][0]),
                            'download_url': data['images'][0]
                        }
                except:
                    pass
                
                # API بديل
                api_url2 = f"https://api.pinterest.com/v1/pins/{pin_id}/?access_token=YOUR_TOKEN"
                try:
                    resp = await client.get(api_url2, timeout=15)
                    data = resp.json()
                    
                    if data.get('data'):
                        pin_data = data['data']
                        if pin_data.get('image'):
                            return {
                                'success': True,
                                'title': pin_data.get('note', 'Pinterest Pin'),
                                'thumbnail': pin_data['image'].get('original', {}).get('url'),
                                'download_url': pin_data['image']['original']['url']
                            }
                except:
                    pass
                
                return {'success': False, 'error': 'فشل تحميل بينترست - حاول رابط آخر'}
        
        # ========== منصات أخرى ==========
        else:
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
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Downloader API v7",
        "platforms": ["youtube", "tiktok", "instagram", "facebook", "twitter", "spotify", "pinterest"]
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
