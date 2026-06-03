from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re
import httpx
from typing import Optional

app = FastAPI(title="Downloader API - Download Only")

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
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower or 'youtube.com/shorts' in url_lower:
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
    elif 'pinterest.com' in url_lower or 'pin.it' in url_lower:
        return 'pinterest'
    else:
        return 'other'

def extract_youtube_id(url: str) -> Optional[str]:
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([^&]+)',
        r'(?:youtu\.be\/)([^?]+)',
        r'(?:youtube\.com\/embed\/)([^/?]+)',
        r'(?:youtube\.com\/shorts\/)([^/?]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# ==================== تحميل يوتيوب ====================
@app.post("/download")
async def download_video(request: DownloadRequest):
    url = request.url
    platform = detect_platform(url)
    
    try:
        # يوتيوب
        if platform == 'youtube':
            video_id = extract_youtube_id(url)
            if not video_id:
                return {'success': False, 'error': 'رابط يوتيوب غير صالح'}
            
            if request.type == 'audio':
                ydl_opts = {'format': 'bestaudio/best', 'quiet': True}
            else:
                ydl_opts = {'format': 'best[height<=720]', 'quiet': True}
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'success': True,
                    'platform': 'youtube',
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'download_url': info.get('url'),
                    'author': info.get('uploader'),
                    'duration': info.get('duration')
                }
        
        # تيك توك
        elif platform == 'tiktok':
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://tikwm.com/api/?url={url}")
                data = resp.json()
                if data.get('code') == 0:
                    return {
                        'success': True,
                        'platform': 'tiktok',
                        'title': data['data'].get('title', 'TikTok Video'),
                        'thumbnail': data['data'].get('cover'),
                        'download_url': data['data'].get('play'),
                        'author': data['data'].get('author', {}).get('unique_id')
                    }
                return {'success': False, 'error': 'فشل تحميل تيك توك'}
        
        # انستقرام
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
                                'platform': 'instagram',
                                'title': result.get('title', 'Instagram Post'),
                                'thumbnail': result.get('thumbnail'),
                                'download_url': download_url
                            }
                except:
                    pass
                
                try:
                    ydl_opts = {'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        if info.get('url'):
                            return {
                                'success': True,
                                'platform': 'instagram',
                                'title': info.get('title', 'Instagram'),
                                'thumbnail': info.get('thumbnail'),
                                'download_url': info.get('url')
                            }
                except:
                    pass
                return {'success': False, 'error': 'فشل تحميل انستقرام'}
        
        # فيسبوك
        elif platform == 'facebook':
            async with httpx.AsyncClient() as client:
                try:
                    ydl_opts = {'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        return {
                            'success': True,
                            'platform': 'facebook',
                            'title': info.get('title', 'Facebook Video'),
                            'thumbnail': info.get('thumbnail'),
                            'download_url': info.get('url')
                        }
                except:
                    pass
                return {'success': False, 'error': 'فشل تحميل فيسبوك'}
        
        # تويتر
        elif platform == 'twitter':
            async with httpx.AsyncClient() as client:
                try:
                    ydl_opts = {'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        return {
                            'success': True,
                            'platform': 'twitter',
                            'title': info.get('title', 'Twitter Video'),
                            'thumbnail': info.get('thumbnail'),
                            'download_url': info.get('url')
                        }
                except:
                    pass
                return {'success': False, 'error': 'فشل تحميل تويتر'}
        
        # سبوتيفاي
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
                            "platform": "spotify",
                            "title": info.get("name"),
                            "thumbnail": info.get("imageHD") or info.get("image"),
                            "download_url": info.get("url"),
                            "author": info.get("artist"),
                            "duration": info.get("duration")
                        }
                except:
                    pass
                return {"success": False, "error": "فشل تحميل سبوتيفاي"}
        
        # بينترست
        elif platform == 'pinterest':
            async with httpx.AsyncClient() as client:
                try:
                    home = await client.get("https://snappin.app/")
                    csrf = re.search(r'name="csrf-token" content="([^"]+)"', home.text)
                    token = csrf.group(1) if csrf else ""
                    cookies = "; ".join([c.split(";")[0] for c in home.headers.get_list("set-cookie")])
                    
                    result = await client.post(
                        "https://snappin.app/",
                        json={"url": url},
                        headers={
                            "x-csrf-token": token,
                            "Cookie": cookies,
                            "Origin": "https://snappin.app",
                            "Referer": "https://snappin.app",
                            "User-Agent": "Mozilla/5.0"
                        },
                        timeout=30
                    )
                    
                    links = re.findall(r'<a[^>]*class="button is-success"[^>]*href="([^"]+)"', result.text)
                    if links:
                        media = links[0]
                        if not media.startswith("http"):
                            media = "https://snappin.app" + media
                        return {
                            "success": True,
                            "platform": "pinterest",
                            "title": "Pinterest Media",
                            "thumbnail": "",
                            "download_url": media
                        }
                except:
                    pass
                return {"success": False, "error": "فشل تحميل بينترست"}
        
        else:
            return {'success': False, 'error': f'المنصة {platform} غير مدعومة'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ==================== خدمات تحميل إضافية ====================

@app.get("/download/mediafire")
async def mediafire(url: str):
    """تحميل ملف من ميديا فاير"""
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
    
    html = r.text
    
    title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
    download = re.search(r'https://download[^\"]+', html)
    
    return {
        "status": True,
        "filename": title.group(1) if title else "Unknown",
        "download_url": download.group(0) if download else None
    }

@app.get("/download/music")
async def music(url: str):
    """تحميل موسيقى MP3 من رابط"""
    async with httpx.AsyncClient() as client:
        key_res = await client.get("https://cnv.cx/v2/sanity/key")
        key = key_res.json()["key"]
        
        conv = await client.post(
            "https://cnv.cx/v2/converter",
            headers={"key": key},
            data={
                "link": url,
                "format": "mp3",
                "audioBitrate": "128",
                "filenameStyle": "pretty"
            }
        )
        data = conv.json()
        
        return {
            "status": True,
            "title": data.get("filename"),
            "download_url": data.get("url")
        }

@app.get("/download/ytmp4")
async def ytmp4(url: str):
    """تحميل فيديو MP4 من يوتيوب"""
    async with httpx.AsyncClient() as client:
        key_data = (await client.get("https://cnv.cx/v2/sanity/key")).json()
        key = key_data["key"]
        
        data = (await client.post(
            "https://cnv.cx/v2/converter",
            headers={"key": key},
            data={
                "link": url,
                "format": "mp4",
                "videoQuality": "720",
                "filenameStyle": "pretty",
                "vCodec": "h264"
            }
        )).json()
        
        return {
            "status": True,
            "filename": data.get("filename"),
            "download_url": data.get("url")
        }

# ==================== دليل API ====================
@app.get("/api/guide")
def api_guide():
    return {
        "status": "ok",
        "message": "واجهات API للتحميل فقط",
        "endpoints": {
            "/download": {
                "method": "POST",
                "description": "تحميل فيديو/صوت من أي منصة (يوتيوب، تيك توك، انستقرام، فيسبوك، تويتر، بينترست، سبوتيفاي)",
                "body": {"url": "الرابط", "type": "video/audio"}
            },
            "/download/mediafire": {
                "method": "GET",
                "description": "تحميل ملف من ميديا فاير",
                "params": {"url": "رابط ميديا فاير"}
            },
            "/download/music": {
                "method": "GET",
                "description": "تحميل موسيقى MP3 من رابط",
                "params": {"url": "رابط الفيديو"}
            },
            "/download/ytmp4": {
                "method": "GET",
                "description": "تحميل فيديو MP4 من يوتيوب",
                "params": {"url": "رابط يوتيوب"}
            }
        }
    }

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Downloader API - تحميل فقط",
        "endpoints": ["/download", "/download/mediafire", "/download/music", "/download/ytmp4"],
        "docs": "/api/guide"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}