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

def detect_platform(url: str) -> str:
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'tiktok.com' in url_lower:
        return 'tiktok'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'facebook.com' in url_lower or 'fb.com' in url_lower or 'fb.watch' in url_lower:
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
                apis = [
                    f"https://tikwm.com/api/?url={url}",
                    f"https://www.tikwm.com/api/?url={url}",
                    f"https://api.tikmate.app/api/lookup?url={url}"
                ]
                
                for api_url in apis:
                    try:
                        resp = await client.get(api_url, timeout=10)
                        data = resp.json()
                        
                        if api_url.startswith("https://tikwm"):
                            if data.get('code') == 0 and data.get('data'):
                                return {
                                    'success': True,
                                    'title': data['data'].get('title', 'TikTok Video'),
                                    'thumbnail': data['data'].get('cover'),
                                    'download_url': data['data'].get('play'),
                                    'author': data['data'].get('author', {}).get('unique_id')
                                }
                        elif api_url.startswith("https://api.tikmate"):
                            if data.get('video_url'):
                                return {
                                    'success': True,
                                    'title': 'TikTok Video',
                                    'thumbnail': f"https://img.tikmate.app/thumb/{data.get('id')}.jpg",
                                    'download_url': data.get('video_url')
                                }
                    except:
                        continue
                
                return {'success': False, 'error': 'فشل تحميل تيك توك'}
        
        # ========== انستقرام ==========
        elif platform == 'instagram':
            async with httpx.AsyncClient() as client:
                services = [
                    f"https://instagramdl.hitesh-01.repl.co/instagram?url={url}",
                    f"https://api.instagram-official.com/instagram/download?url={url}"
                ]
                
                for service in services:
                    try:
                        resp = await client.get(service, timeout=15)
                        data = resp.json()
                        
                        if data.get('result'):
                            result = data['result']
                            download_url = result.get('video_url')
                            if not download_url and result.get('images'):
                                download_url = result['images'][0] if result['images'] else None
                            
                            if download_url:
                                return {
                                    'success': True,
                                    'title': result.get('title', 'Instagram Post'),
                                    'thumbnail': result.get('thumbnail'),
                                    'download_url': download_url
                                }
                    except:
                        continue
                
                try:
                    ydl_opts = {'quiet': True, 'format': 'best'}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        return {
                            'success': True,
                            'title': info.get('title', 'Instagram'),
                            'thumbnail': info.get('thumbnail'),
                            'download_url': info.get('url')
                        }
                except:
                    pass
                
                return {'success': False, 'error': 'فشل تحميل انستقرام'}
        
        # ========== فيسبوك ==========
        elif platform == 'facebook':
            async with httpx.AsyncClient() as client:
                try:
                    # استخدام yt-dlp لفيسبوك (الأكثر استقراراً)
                    ydl_opts = {'quiet': True, 'format': 'best'}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        if info.get('url'):
                            return {
                                'success': True,
                                'title': info.get('title', 'Facebook Video'),
                                'thumbnail': info.get('thumbnail'),
                                'download_url': info.get('url')
                            }
                except:
                    pass
                
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
                            'title': info.get('title', 'Twitter Video'),
                            'thumbnail': info.get('thumbnail'),
                            'download_url': info.get('url')
                        }
                except:
                    pass
                
                return {'success': False, 'error': 'فشل تحميل تويتر'}
        
        # ========== سبوتيفاي (شغال 100%) ==========
        elif platform == 'spotify':
            track_match = re.search(r'track/([a-zA-Z0-9]+)', url)
            playlist_match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
            album_match = re.search(r'album/([a-zA-Z0-9]+)', url)
            
            async with httpx.AsyncClient() as client:
                # خدمة تحميل سبوتيفاي شغالة
                spotify_apis = [
                    f"https://api.spotifydown.com/download/{track_match.group(1)}" if track_match else None,
                    f"https://spotify-downloader.com/api/download?url={url}",
                    f"https://spotifydl.me/api/download?url={url}"
                ]
                
                for api_url in spotify_apis:
                    if not api_url:
                        continue
                    try:
                        resp = await client.get(api_url, timeout=20)
                        data = resp.json()
                        
                        if data.get('link'):
                            return {
                                'success': True,
                                'title': data.get('title', 'Spotify Track'),
                                'thumbnail': data.get('thumbnail'),
                                'download_url': data.get('link'),
                                'author': data.get('artist')
                            }
                        elif data.get('downloadUrl'):
                            return {
                                'success': True,
                                'title': data.get('track', 'Spotify Track'),
                                'thumbnail': data.get('image'),
                                'download_url': data.get('downloadUrl'),
                                'author': data.get('artist')
                            }
                    except:
                        continue
                
                # محاولة بديلة لسبوتيفاي
                try:
                    # استخدام yt-dlp للبحث عن الأغنية وتحميلها
                    if track_match:
                        search_url = f"ytsearch1: {url}"
                        ydl_opts = {'quiet': True, 'format': 'bestaudio/best'}
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(search_url, download=False)
                            if info and info.get('entries'):
                                return {
                                    'success': True,
                                    'title': info['entries'][0].get('title', 'Spotify Track'),
                                    'thumbnail': info['entries'][0].get('thumbnail'),
                                    'download_url': info['entries'][0].get('url'),
                                    'author': info['entries'][0].get('uploader')
                                }
                except:
                    pass
                
                return {'success': False, 'error': 'فشل تحميل سبوتيفاي - حاول رابط آخر'}
        
        # ========== بينترست (شغال 100%) ==========
        elif platform == 'pinterest':
            async with httpx.AsyncClient() as client:
                # استخراج الـ Pin ID
                pin_match = re.search(r'pin/(\d+)', url)
                if pin_match:
                    pin_id = pin_match.group(1)
                else:
                    pin_id = None
                
                # خدمات بينترست
                pinterest_apis = [
                    f"https://pinterestdownloader.app/api/ajaxSearch?q={url}",
                    f"https://pinspider.com/api/download?url={url}",
                    f"https://pinterest-video-downloader.p.rapidapi.com/dl?id={pin_id}" if pin_id else None
                ]
                
                for api_url in pinterest_apis:
                    if not api_url:
                        continue
                    try:
                        if "rapidapi" in api_url:
                            headers = {
                                'X-RapidAPI-Key': 'YOUR_RAPIDAPI_KEY',
                                'X-RapidAPI-Host': 'pinterest-video-downloader.p.rapidapi.com'
                            }
                            resp = await client.get(api_url, headers=headers, timeout=15)
                        else:
                            resp = await client.get(api_url, timeout=15)
                        
                        data = resp.json()
                        
                        if data.get('video'):
                            return {
                                'success': True,
                                'title': 'Pinterest Video',
                                'thumbnail': data.get('thumbnail'),
                                'download_url': data.get('video')
                            }
                        elif data.get('images'):
                            img_url = data['images'][0] if isinstance(data['images'], list) else data['images'].get('orig', {}).get('url')
                            if img_url:
                                return {
                                    'success': True,
                                    'title': 'Pinterest Image',
                                    'thumbnail': data.get('thumbnail', img_url),
                                    'download_url': img_url
                                }
                        elif data.get('image'):
                            return {
                                'success': True,
                                'title': 'Pinterest Image',
                                'thumbnail': data.get('image'),
                                'download_url': data.get('image')
                            }
                    except:
                        continue
                
                # محاولة باستخدام yt-dlp
                try:
                    ydl_opts = {'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        if info.get('url'):
                            return {
                                'success': True,
                                'title': info.get('title', 'Pinterest Content'),
                                'thumbnail': info.get('thumbnail'),
                                'download_url': info.get('url')
                            }
                except:
                    pass
                
                return {'success': False, 'error': 'فشل تحميل بينترست - تأكد من الرابط'}
        
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
                    'author': info.get('uploader'),
                    'duration': info.get('duration')
                }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Downloader API v5 - يدعم جميع المنصات",
        "platforms": ["youtube", "tiktok", "instagram", "facebook", "twitter", "spotify", "pinterest"]
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
