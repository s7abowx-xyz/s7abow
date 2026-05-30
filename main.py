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
    recaptcha_token: Optional[str] = None
    user: Optional[str] = None

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

# ========== دالة التحقق من reCAPTCHA ==========
async def verify_recaptcha(token: str):
    """التحقق من أن المستخدم إنسان باستخدام Google reCAPTCHA"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": "YOUR_SECRET_KEY", "response": token}
            )
            result = resp.json()
            return result.get("success", False)
    except Exception as e:
        print(f"reCAPTCHA verification error: {e}")
        return False

@app.post("/download")
async def download_video(request: DownloadRequest):
    url = request.url
    platform = detect_platform(url)
    
    # ========== التحقق من reCAPTCHA ==========
    if request.recaptcha_token:
        is_human = await verify_recaptcha(request.recaptcha_token)
        if not is_human:
            return {'success': False, 'error': 'فشل التحقق - يرجى المحاولة مرة أخرى'}
    
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
                try:
                    resp = await client.get(f"https://instagramdl.hitesh-01.repl.co/instagram?url={url}", timeout=15)
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
                    pass
                
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
                            "album": info.get("album"),
                            "duration": info.get("duration")
                        }
                except Exception:
                    pass
                
                return {"success": False, "error": "Spotify download failed"}
        
        # ========== بينترست ==========
        elif platform == 'pinterest':
            async with httpx.AsyncClient() as client:
                try:
                    home = await client.get("https://snappin.app/")
                    
                    csrf = re.search(r'name="csrf-token" content="([^"]+)"', home.text)
                    csrf_token = csrf.group(1) if csrf else ""
                    
                    cookies = "; ".join([x.split(";")[0] for x in home.headers.get_list("set-cookie")])
                    
                    resp = await client.post(
                        "https://snappin.app/",
                        json={"url": url},
                        headers={
                            "x-csrf-token": csrf_token,
                            "Cookie": cookies,
                            "Origin": "https://snappin.app",
                            "Referer": "https://snappin.app",
                            "User-Agent": "Mozilla/5.0"
                        },
                        timeout=30
                    )
                    
                    html = resp.text
                    links = re.findall(r'<a[^>]*class="button is-success"[^>]*href="([^"]+)"', html)
                    
                    if links:
                        media = links[0]
                        if not media.startswith("http"):
                            media = "https://snappin.app" + media
                        
                        return {
                            "success": True,
                            "title": "Pinterest Media",
                            "download_url": media
                        }
                except Exception:
                    pass
                
                return {"success": False, "error": "Pinterest download failed"}
        
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
        "message": "Downloader API - يدعم جميع المنصات",
        "platforms": ["youtube", "tiktok", "instagram", "facebook", "twitter", "spotify", "pinterest"]
    }

@app.get("/health")
def health():
    return {"status": "healthy"}