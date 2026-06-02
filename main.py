from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re
import httpx
from typing import Optional, List
import requests

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
    type: Optional[str] = "video"
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

# ========== دالة البحث في يوتيوب ==========
def search_youtube(query: str, search_type: str = 'video', limit: int = 10) -> List[dict]:
    results = []
    search_query = f"ytsearch{limit}:{query}"
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
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

# ========== 1. البحث في جوجل صور ==========
@app.get("/search/googleimage")
async def googleimage(query: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.evogb.org/search/googleimage?query={query}&key=sasuke"
        )
        return r.json()

# ========== 2. تحميل من ميديا فاير ==========
@app.get("/download/mediafire")
async def mediafire(url: str):
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

# ========== 3. البحث في سبوتيفاي ==========
@app.get("/search/spotify")
async def spotify_search(query: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.evogb.org/search/spotify?query={query}&key=sasuke"
        )
        return r.json()

# ========== 4. تحميل موسيقى ==========
@app.get("/download/music")
async def music(url: str):
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

# ========== 5. تحميل فيديو MP4 من يوتيوب ==========
@app.get("/download/ytmp4")
async def ytmp4(url: str):
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

# ========== 6. البحث في بينترست ==========
@app.get("/search/pinterest")
async def pinterest_search(query: str, limit: int = 20):
    url = f"https://id.pinterest.com/resource/BaseSearchResource/get/?source_url=%2Fsearch%2Fpins%2F%3Fq%3D{query}%26rs%3Dtyped&data=%7B%22options%22%3A%7B%22query%22%3A%22{query}%22%2C%22scope%22%3A%22pins%22%2C%22rs%22%3A%22typed%22%7D%2C%22context%22%3A%7B%7D%7D"
    
    headers = {
        "x-requested-with": "XMLHttpRequest",
        "user-agent": "Mozilla/5.0"
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers)
        data = res.json()
        
        results = []
        if 'resource_response' in data and 'data' in data['resource_response']:
            for item in data['resource_response']['data'][:limit]:
                results.append({
                    'id': item.get('id'),
                    'title': item.get('title', 'No title'),
                    'image': item.get('images', {}).get('orig', {}).get('url', ''),
                    'link': f"https://pinterest.com/pin/{item.get('id')}"
                })
        
        return {
            "status": True,
            "query": query,
            "count": len(results),
            "results": results
        }

# ========== 7. البحث في تيك توك ==========
@app.get("/search/tiktok")
async def tiktok_search(query: str, count: int = 20):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://tikwm.com/api/feed/search",
            data={
                "keywords": query,
                "count": count,
                "cursor": 0,
                "HD": 1
            },
            headers={
                "Cookie": "current_language=en",
                "User-Agent": "Mozilla/5.0"
            }
        )
        data = res.json()
        
        results = []
        if data.get('code') == 0 and data.get('data'):
            for item in data['data'].get('videos', []):
                results.append({
                    'id': item.get('id'),
                    'title': item.get('title'),
                    'duration': item.get('duration'),
                    'play_count': item.get('play_count'),
                    'likes': item.get('digg_count'),
                    'comments': item.get('comment_count'),
                    'shares': item.get('share_count'),
                    'thumbnail': item.get('cover'),
                    'video_url': item.get('play'),
                    'author': item.get('author', {}).get('unique_id'),
                    'author_avatar': item.get('author', {}).get('avatar')
                })
        
        return {
            "status": True,
            "query": query,
            "count": len(results),
            "results": results
        }

# ========== 8. البحث العام (يوتيوب) ==========
@app.post("/search")
async def search(request: SearchRequest):
    try:
        results = search_youtube(request.query, request.type, request.limit)
        return {
            'success': True,
            'query': request.query,
            'type': request.type,
            'count': len(results),
            'results': results
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ========== 9. تحميل عام من أي منصة ==========
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

# ========== 10. دليل API ==========
@app.get("/api/guide")
def api_guide():
    return {
        "status": "ok",
        "message": "دليل استخدام API - جميع الخدمات المتاحة",
        "endpoints": {
            "GET /search/googleimage": {
                "description": "البحث في جوجل صور",
                "params": {"query": "كلمة البحث"},
                "example": "/search/googleimage?query=طبيعة"
            },
            "GET /download/mediafire": {
                "description": "تحميل ملف من ميديا فاير",
                "params": {"url": "رابط ميديا فاير"},
                "example": "/download/mediafire?url=https://www.mediafire.com/file/..."
            },
            "GET /search/spotify": {
                "description": "البحث في سبوتيفاي",
                "params": {"query": "كلمة البحث"},
                "example": "/search/spotify?query=اغنية"
            },
            "GET /download/music": {
                "description": "تحميل موسيقى من رابط",
                "params": {"url": "رابط الفيديو"},
                "example": "/download/music?url=https://youtube.com/watch?v=..."
            },
            "GET /download/ytmp4": {
                "description": "تحميل فيديو MP4 من يوتيوب",
                "params": {"url": "رابط يوتيوب"},
                "example": "/download/ytmp4?url=https://youtube.com/watch?v=..."
            },
            "GET /search/pinterest": {
                "description": "البحث في بينترست",
                "params": {"query": "كلمة البحث", "limit": "عدد النتائج"},
                "example": "/search/pinterest?query=طبيعة&limit=10"
            },
            "GET /search/tiktok": {
                "description": "البحث في تيك توك",
                "params": {"query": "كلمة البحث", "count": "عدد النتائج"},
                "example": "/search/tiktok?query=naruto&count=20"
            },
            "POST /search": {
                "description": "البحث العام في يوتيوب",
                "body": {"query": "كلمة البحث", "type": "video/audio", "limit": 10}
            },
            "POST /download": {
                "description": "تحميل من أي منصة",
                "body": {"url": "الرابط", "type": "video/audio"}
            }
        }
    }

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Universal Downloader API - يدعم جميع الخدمات",
        "endpoints_count": 9,
        "docs": "/api/guide"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}