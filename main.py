from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re
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

# دالة عامة للتحميل باستخدام yt-dlp
def download_with_ytdlp(url: str, is_audio: bool = False):
    if is_audio:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
        }
    else:
        ydl_opts = {
            'format': 'best[height<=720]',
            'quiet': True,
            'no_warnings': True,
        }
    
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

@app.post("/download")
async def download_video(request: DownloadRequest):
    url = request.url
    platform = detect_platform(url)
    
    try:
        # ========== يوتيوب ==========
        if platform == 'youtube':
            result = download_with_ytdlp(url, request.type == 'audio')
            return result
        
        # ========== تيك توك ==========
        elif platform == 'tiktok':
            result = download_with_ytdlp(url, False)
            return result
        
        # ========== انستقرام ==========
        elif platform == 'instagram':
            result = download_with_ytdlp(url, False)
            return result
        
        # ========== فيسبوك ==========
        elif platform == 'facebook':
            result = download_with_ytdlp(url, False)
            return result
        
        # ========== تويتر ==========
        elif platform == 'twitter':
            result = download_with_ytdlp(url, False)
            return result
        
        # ========== سبوتيفاي ==========
        elif platform == 'spotify':
            # سبوتيفاي: نحول الرابط إلى بحث في يوتيوب
            # استخراج اسم الأغنية من الرابط
            track_match = re.search(r'track/([a-zA-Z0-9]+)', url)
            if track_match:
                # نستخدم yt-dlp للبحث عن الأغنية في يوتيوب
                search_query = f"ytsearch1:{url}"
                ydl_opts = {
                    'quiet': True,
                    'extract_flat': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(search_query, download=False)
                    if info and info.get('entries') and len(info['entries']) > 0:
                        video_url = f"https://youtube.com/watch?v={info['entries'][0]['id']}"
                        # تحميل الصوت من الفيديو
                        result = download_with_ytdlp(video_url, True)
                        return result
            
            return {'success': False, 'error': 'فشل تحميل سبوتيفاي - تأكد من الرابط'}
        
        # ========== بينترست ==========
        elif platform == 'pinterest':
            try:
                result = download_with_ytdlp(url, False)
                return result
            except Exception as e:
                # إذا فشل yt-dlp، نجرب طريقة بديلة
                import httpx
                async with httpx.AsyncClient() as client:
                    # محاولة استخراج الـ Pin ID
                    pin_match = re.search(r'pin/(\d+)', url)
                    if pin_match:
                        pin_id = pin_match.group(1)
                        # استخدام API بسيط
                        resp = await client.get(f"https://api.pinterest.com/v3/pidgets/pins/{pin_id}/", timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get('data'):
                                pin_data = data['data']
                                # البحث عن فيديو أو صورة
                                if pin_data.get('video'):
                                    return {
                                        'success': True,
                                        'title': pin_data.get('title', 'Pinterest'),
                                        'thumbnail': pin_data.get('image', {}).get('original', {}).get('url'),
                                        'download_url': pin_data['video'].get('url')
                                    }
                                elif pin_data.get('image'):
                                    return {
                                        'success': True,
                                        'title': pin_data.get('title', 'Pinterest'),
                                        'thumbnail': pin_data['image'].get('original', {}).get('url'),
                                        'download_url': pin_data['image']['original']['url']
                                    }
                return {'success': False, 'error': 'فشل تحميل بينترست - تأكد من الرابط'}
        
        # ========== منصات أخرى ==========
        else:
            result = download_with_ytdlp(url, request.type == 'audio')
            return result
        
    except Exception as e:
        error_msg = str(e)
        return {'success': False, 'error': error_msg}

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Downloader API v6 - يدعم جميع المنصات باستخدام yt-dlp",
        "platforms": ["youtube", "tiktok", "instagram", "facebook", "twitter", "spotify", "pinterest"]
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
