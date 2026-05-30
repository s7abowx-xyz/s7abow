from fastapi import FastAPI
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
                    'author': info.get('uploader'),
                    'duration': info.get('duration')
                }
        
        # ========== تيك توك ==========
        elif platform == 'tiktok':
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://tikwm.com/api/?url={url}")
                data = resp.json()
                if data.get('code') == 0:
                    return {
                        'success': True,
                        'title': data['data'].get('title', 'TikTok Video'),
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
                    download_url = result.get('video_url')
                    if not download_url and result.get('images'):
                        download_url = result['images'][0] if result['images'] else None
                    return {
                        'success': True,
                        'title': 'Instagram Post',
                        'thumbnail': result.get('thumbnail'),
                        'download_url': download_url
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
                            'title': info.get('title', 'Facebook Video'),
                            'thumbnail': info.get('thumbnail'),
                            'download_url': info.get('url')
                        }
                except:
                    pass
        
        # ========== تويتر ==========
        elif platform == 'twitter':
            async with httpx.AsyncClient() as client:
                try:
                    ydl_opts = {'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        return {
                            'success': True,
                            'title': info.get('title', 'Twitter Video'),
                            'thumbnail': info.get('thumbnail'),
                            'download_url': info.get('url')
                        }
                except:
                    pass
        
        # ========== سبوتيفاي ==========
        elif platform == 'spotify':
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(
                        f"https://api.evogb.org/dl/spotify?url={url}&key=sasuke",
                        timeout=30
                    )
                    data = resp.json()
                    
                    if data.get("status"):
                        info = data.get("data", {})
                        return {
                            "success": True,
                            "title": info.get("name"),
                            "thumbnail": info.get("imageHD") or info.get("image"),
                            "download_url": info.get("url"),
                            "author": info.get("artist"),
                            "duration": info.get("duration")
                        }
                except:
                    pass
                
                return {"success": False, "error": "Spotify download failed"}
        
        # ========== بينترست - حل جديد ==========
        elif platform == 'pinterest':
            async with httpx.AsyncClient() as client:
                # استخراج الـ Pin ID
                pin_match = re.search(r'pin/(\d+)', url)
                if not pin_match:
                    return {'success': False, 'error': 'رابط بينترست غير صالح'}
                
                pin_id = pin_match.group(1)
                
                # استخدام API Pinterest
                try:
                    resp = await client.get(
                        f"https://api.pinterest.com/v3/pidgets/pins/{pin_id}/",
                        timeout=30
                    )
                    data = resp.json()
                    
                    if data.get('data'):
                        pin_data = data['data']
                        
                        # صورة
                        if pin_data.get('image'):
                            img_url = pin_data['image'].get('original', {}).get('url')
                            if img_url:
                                return {
                                    'success': True,
                                    'title': pin_data.get('note', 'Pinterest Image'),
                                    'thumbnail': img_url,
                                    'download_url': img_url
                                }
                        
                        # فيديو
                        if pin_data.get('video'):
                            video_url = pin_data['video'].get('url')
                            if video_url:
                                return {
                                    'success': True,
                                    'title': pin_data.get('note', 'Pinterest Video'),
                                    'thumbnail': pin_data.get('image', {}).get('original', {}).get('url'),
                                    'download_url': video_url
                                }
                except:
                    pass
                
                return {'success': False, 'error': 'فشل تحميل بينترست'}
        
        return {'success': False, 'error': f'المنصة {platform} غير مدعومة'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Downloader API - يدعم جميع المنصات",
        "platforms": ["youtube", "tiktok", "instagram", "facebook", "twitter", "spotify", "pinterest"]
                    }
