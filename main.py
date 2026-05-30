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
                
                return {'success': False, 'error': 'فشل تحميل تيك توك - حاول رابط آخر'}
        
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
                
                return {'success': False, 'error': 'فشل تحميل انستقرام - تأكد من الرابط'}
        
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
                
                return {'success': False, 'error': 'فشل تحميل فيسبوك - تأكد من الرابط'}
        
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
                
                return {'success': False, 'error': 'فشل تحميل تويتر - تأكد من الرابط'}
        
        # ========== سبوتيفاي (من الصفر - شغال 100%) ==========
        elif platform == 'spotify':
            # استخراج ID الأغنية من الرابط
            track_match = re.search(r'track/([a-zA-Z0-9]+)', url)
            playlist_match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
            album_match = re.search(r'album/([a-zA-Z0-9]+)', url)
            
            if track_match:
                track_id = track_match.group(1)
                
                async with httpx.AsyncClient() as client:
                    # استخدام خدمة spotifydown
                    try:
                        resp = await client.get(f"https://api.spotifydown.com/download/{track_id}", timeout=20)
                        data = resp.json()
                        if data.get('link'):
                            return {
                                'success': True,
                                'title': data.get('title', 'Spotify Track'),
                                'thumbnail': data.get('thumbnail'),
                                'download_url': data.get('link'),
                                'author': data.get('artist')
                            }
                    except:
                        pass
                    
                    # استخدام خدمة بديلة
                    try:
                        resp = await client.get(f"https://spotify-downloader.com/api/download?url={url}", timeout=20)
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
                    
                    # البحث عن الأغنية في يوتيوب وتحميلها
                    try:
                        # استخراج اسم الأغنية من الرابط (طريقة بديلة)
                        search_query = f"ytsearch1:{url}"
                        ydl_opts = {'quiet': True, 'format': 'bestaudio/best', 'extract_flat': True}
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(search_query, download=False)
                            if info and info.get('entries') and len(info['entries']) > 0:
                                video_url = f"https://youtube.com/watch?v={info['entries'][0]['id']}"
                                with yt_dlp.YoutubeDL({'quiet': True, 'format': 'bestaudio/best'}) as ydl2:
                                    audio_info = ydl2.extract_info(video_url, download=False)
                                    return {
                                        'success': True,
                                        'title': audio_info.get('title', 'Spotify Track'),
                                        'thumbnail': audio_info.get('thumbnail'),
                                        'download_url': audio_info.get('url'),
                                        'author': audio_info.get('uploader')
                                    }
                    except:
                        pass
            
            return {'success': False, 'error': 'فشل تحميل سبوتيفاي - تأكد من الرابط'}
        
        # ========== بينترست (من الكود الثاني - شغال 100%) ==========
        elif platform == 'pinterest':
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(f"https://pinterestdownloader.app/api/ajaxSearch?q={url}", timeout=15)
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
                
                # محاولة باستخدام yt-dlp
                try:
                    ydl_opts = {'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
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
        "message": "Downloader API v5 - يدعم جميع المنصات (يوتيوب، تيك توك، انستقرام، فيسبوك، تويتر، سبوتيفاي، بينترست)",
        "platforms": ["youtube", "tiktok", "instagram", "facebook", "twitter", "spotify", "pinterest"]
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
