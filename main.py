from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re
import httpx
from typing import Optional, List

app = FastAPI(title="Downloader API - Universal")

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

class SearchRequest(BaseModel):
    query: str
    type: Optional[str] = "video"  # video, audio, all
    limit: Optional[int] = 10

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

# ========== دالة البحث ==========
def search_youtube(query: str, search_type: str = 'video', limit: int = 10) -> List[dict]:
    """البحث في يوتيوب وجلب النتائج"""
    results = []
    
    if search_type == 'audio':
        search_query = f"ytsearch{limit}:{query} audio"
    elif search_type == 'video':
        search_query = f"ytsearch{limit}:{query}"
    else:
        search_query = f"ytsearch{limit}:{query}"
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'force_generic_extractor': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search_query, download=False)
            if info and 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        result = {
                            'id': entry.get('id'),
                            'title': entry.get('title'),
                            'duration': entry.get('duration'),
                            'thumbnail': f"https://img.youtube.com/vi/{entry.get('id')}/mqdefault.jpg",
                            'url': f"https://youtube.com/watch?v={entry.get('id')}",
                            'author': entry.get('uploader', 'Unknown')
                        }
                        results.append(result)
        except Exception as e:
            print(f"Search error: {e}")
    
    return results

def search_spotify(query: str, limit: int = 10) -> List[dict]:
    """البحث في سبوتيفاي"""
    results = []
    try:
        # استخدام API سبوتيفاي للبحث
        search_query = query.replace(' ', '%20')
        url = f"https://api.spotify.com/v1/search?q={search_query}&type=track&limit={limit}"
        # ملاحظة: هذا يحتاج token، نستخدم طريقة بديلة
    except:
        pass
    return results

# ========== Endpoint البحث ==========
@app.post("/search")
async def search(request: SearchRequest):
    """البحث عن فيديوهات أو أغاني"""
    try:
        results = []
        
        if request.type == 'audio':
            # بحث عن أغاني
            search_results = search_youtube(request.query, 'audio', request.limit)
            for r in search_results:
                results.append({
                    'type': 'audio',
                    'id': r['id'],
                    'title': r['title'],
                    'duration': r['duration'],
                    'thumbnail': r['thumbnail'],
                    'url': r['url'],
                    'author': r['author']
                })
        else:
            # بحث عن فيديوهات
            search_results = search_youtube(request.query, 'video', request.limit)
            for r in search_results:
                results.append({
                    'type': 'video',
                    'id': r['id'],
                    'title': r['title'],
                    'duration': r['duration'],
                    'thumbnail': r['thumbnail'],
                    'url': r['url'],
                    'author': r['author']
                })
        
        return {
            'success': True,
            'query': request.query,
            'type': request.type,
            'count': len(results),
            'results': results
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ========== Endpoint التحميل ==========
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

# ========== Endpoint API Guide ==========
@app.get("/api/guide")
def api_guide():
    return {
        "status": "ok",
        "message": "دليل استخدام API",
        "endpoints": {
            "POST /search": {
                "description": "البحث عن فيديوهات أو أغاني",
                "body": {
                    "query": "كلمة البحث",
                    "type": "video أو audio",
                    "limit": "عدد النتائج (1-20)"
                },
                "example": {
                    "query": "اغاني حزينة",
                    "type": "audio",
                    "limit": 5
                }
            },
            "POST /download": {
                "description": "تحميل فيديو أو صوت من رابط",
                "body": {
                    "url": "رابط الفيديو",
                    "type": "video أو audio"
                },
                "example": {
                    "url": "https://youtube.com/watch?v=...",
                    "type": "video"
                }
            }
        },
        "platforms": ["youtube", "tiktok", "instagram", "facebook", "twitter", "spotify", "pinterest"]
    }

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Universal Downloader API - يدعم البحث والتحميل",
        "endpoints": {
            "POST /search": "البحث عن فيديوهات/أغاني",
            "POST /download": "تحميل فيديو/صوت من أي منصة",
            "GET /api/guide": "دليل استخدام API",
            "GET /health": "فحص صحة الـ API"
        }
    }

@app.get("/health")
def health():
    return {"status": "healthy"}