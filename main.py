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
            # استخدام API مجاني لتيك توك
            async with httpx.AsyncClient() as client:
                # تجربة أكثر من API
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
                # استخدام خدمة خارجية لانستقرام
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
                
                # محاولة باستخدام yt-dlp
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
                # خدمة تحميل فيسبوك
                fb_apis = [
                    f"https://getvideo.p.rapidapi.com/?url={url}",
                    f"https://fbdown.net/api/ajaxSearch?q={url}"
                ]
                
                for api_url in fb_apis:
                    try:
                        if "rapidapi" in api_url:
                            headers = {
                                'X-RapidAPI-Key': 'YOUR_RAPIDAPI_KEY',  # سجل في RapidAPI وخذ مفتاح
                                'X-RapidAPI-Host': 'getvideo.p.rapidapi.com'
                            }
                            resp = await client.get(api_url, headers=headers, timeout=15)
                        else:
                            resp = await client.post(api_url, 
                                data={'q': url},
                                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                timeout=15)
                        
                        data = resp.json()
                        
                        if data.get('sd') or data.get('hd'):
                            return {
                                'success': True,
                                'title': data.get('title', 'Facebook Video'),
                                'thumbnail': data.get('thumb'),
                                'download_url': data.get('hd') or data.get('sd')
                            }
                        elif data.get('links'):
                            return {
                                'success': True,
                                'title': 'Facebook Video',
                                'download_url': data['links'].get('Download High Quality') or data['links'].get('Download Low Quality')
                            }
                    except:
                        continue
                
                # محاولة باستخدام yt-dlp
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
                twitter_apis = [
                    "https://twitsave.com/api/ajaxSearch",
                    "https://twittervid.com/api/ajaxSearch"
                ]
                
                for api_url in twitter_apis:
                    try:
                        resp = await client.post(api_url,
                            data={'q': url},
                            headers={'Content-Type': 'application/x-www-form-urlencoded'},
                            timeout=15)
                        data = resp.json()
                        
                        if data.get('medias'):
                            for media in data['medias']:
                                if media.get('type') == 'video':
                                    return {
                                        'success': True,
                                        'title': 'Twitter Video',
                                        'thumbnail': data.get('thumbnail'),
                                        'download_url': media.get('url')
                                    }
                    except:
                        continue
                
                # محاولة باستخدام yt-dlp
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
        
        # ========== سبوتيفاي ==========
        elif platform == 'spotify':
            track_match = re.search(r'track/([a-zA-Z0-9]+)', url)
            if track_match:
                async with httpx.AsyncClient() as client:
                    try:
                        resp = await client.get(f"https://api.spotifydown.com/download/{track_match.group(1)}", timeout=15)
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
                return {'success': False, 'error': 'فشل تحميل سبوتيفاي'}
        
        # ========== بينترست ==========
        elif platform == 'pinterest':
            async with httpx.AsyncClient() as client:
                # استخراج الـ Pin ID
                pin_match = re.search(r'pin/(\d+)', url)
                if pin_match:
                    pin_id = pin_match.group(1)
                else:
                    pin_id = None
                
                services = [
                    f"https://pinterestdownloader.app/api/ajaxSearch?q={url}",
                    f"https://api.pinterest.com/v1/pins/{pin_id}/?access_token=YOUR_TOKEN" if pin_id else None
                ]
                
                for service in services:
                    if not service:
                        continue
                    try:
                        resp = await client.get(service, timeout=15)
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
                    except:
                        continue
                
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
        
        return {'success': False, 'error': 'فشل تحميل المحتوى - المنصة غير مدعومة أو الرابط غير صالح'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Downloader API v4 - يدعم: يوتيوب، تيك توك، انستقرام، فيسبوك، تويتر، سبوتيفاي، بينترست",
        "platforms": ["youtube", "tiktok", "instagram", "facebook", "twitter", "spotify", "pinterest"]
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
