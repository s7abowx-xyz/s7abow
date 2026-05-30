from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re
import httpx
import json
import os
import hashlib
from typing import Optional
from datetime import datetime

app = FastAPI(title="Downloader API", description="API لتحميل من جميع المنصات")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== ملفات البيانات ==========
USERS_FILE = "users.json"
STATS_FILE = "stats.json"
SETTINGS_FILE = "settings.json"

def load_json(file):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

# ========== إعدادات المنصات ==========
def get_settings():
    settings = load_json(SETTINGS_FILE)
    if not settings:
        settings = {
            "youtube": True,
            "tiktok": True,
            "instagram": True,
            "facebook": True,
            "twitter": True,
            "spotify": True,
            "pinterest": True
        }
        save_json(SETTINGS_FILE, settings)
    return settings

# ========== دوال المستخدمين ==========
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ========== نماذج البيانات ==========
class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class DownloadRequest(BaseModel):
    url: str
    type: Optional[str] = "video"
    user: Optional[str] = None

class PlatformToggleRequest(BaseModel):
    platform: str
    enabled: bool
    password: str

# ========== API Endpoints ==========

@app.post("/register")
async def register(request: RegisterRequest):
    """إنشاء حساب جديد"""
    users = load_json(USERS_FILE)
    
    if not request.username or not request.password:
        return {"success": False, "error": "الرجاء ملء جميع الحقول"}
    
    if request.username in users:
        return {"success": False, "error": "اسم المستخدم موجود بالفعل"}
    
    users[request.username] = {
        "password": hash_password(request.password),
        "created_at": datetime.now().isoformat(),
        "downloads": 0
    }
    save_json(USERS_FILE, users)
    
    return {"success": True, "message": "تم إنشاء الحساب بنجاح"}

@app.post("/login")
async def login(request: LoginRequest):
    """تسجيل الدخول"""
    users = load_json(USERS_FILE)
    
    if not request.username or not request.password:
        return {"success": False, "error": "الرجاء ملء جميع الحقول"}
    
    if request.username not in users:
        return {"success": False, "error": "اسم المستخدم غير موجود"}
    
    if users[request.username]["password"] != hash_password(request.password):
        return {"success": False, "error": "كلمة المرور غير صحيحة"}
    
    return {
        "success": True, 
        "user": request.username,
        "downloads": users[request.username].get("downloads", 0)
    }

@app.post("/admin/stats")
async def admin_stats(request: dict):
    """إحصائيات الموقع (للمطور فقط)"""
    if request.get("password") != "s7abow":
        return {"success": False, "error": "كلمة المرور غير صحيحة"}
    
    users = load_json(USERS_FILE)
    stats = load_json(STATS_FILE)
    
    return {
        "success": True,
        "stats": {
            "total_users": len(users),
            "total_downloads": stats.get("total_downloads", 0),
            "platforms": stats.get("platforms", {}),
            "top_users": sorted(stats.get("users", {}).items(), key=lambda x: x[1], reverse=True)[:5]
        }
    }

@app.post("/admin/settings")
async def admin_settings(request: PlatformToggleRequest):
    """تغيير إعدادات المنصات"""
    if request.password != "s7abow":
        return {"success": False, "error": "كلمة المرور غير صحيحة"}
    
    settings = get_settings()
    settings[request.platform] = request.enabled
    save_json(SETTINGS_FILE, settings)
    return {"success": True, "settings": settings}

@app.get("/admin/settings")
async def get_admin_settings():
    return {"success": True, "settings": get_settings()}

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
    elif 'pinterest.com' in url_lower or 'pin.it' in url_lower:
        return 'pinterest'
    else:
        return 'other'

def update_stats(username: str, platform: str):
    """تحديث إحصائيات التحميل"""
    stats = load_json(STATS_FILE)
    
    if "total_downloads" not in stats:
        stats["total_downloads"] = 0
    stats["total_downloads"] += 1
    
    if "platforms" not in stats:
        stats["platforms"] = {}
    if platform not in stats["platforms"]:
        stats["platforms"][platform] = 0
    stats["platforms"][platform] += 1
    
    if "users" not in stats:
        stats["users"] = {}
    if username not in stats["users"]:
        stats["users"][username] = 0
    stats["users"][username] += 1
    
    stats["last_download"] = datetime.now().isoformat()
    save_json(STATS_FILE, stats)
    
    # تحديث عدد تحميلات المستخدم
    users = load_json(USERS_FILE)
    if username in users:
        users[username]["downloads"] = stats["users"][username]
        save_json(USERS_FILE, users)

@app.post("/download")
async def download_video(request: DownloadRequest):
    url = request.url
    platform = detect_platform(url)
    
    # التحقق من إعدادات المنصة
    settings = get_settings()
    if not settings.get(platform, True):
        return {'success': False, 'error': f'❌ منصة {platform} معطلة حالياً'}
    
    try:
        # ========== يوتيوب ==========
        if platform == 'youtube':
            if request.type == 'audio':
                ydl_opts = {'format': 'bestaudio/best', 'quiet': True}
            else:
                ydl_opts = {'format': 'best[height<=720]', 'quiet': True}
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if request.user:
                    update_stats(request.user, platform)
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
                                if request.user:
                                    update_stats(request.user, platform)
                                return {
                                    'success': True,
                                    'title': data['data'].get('title', 'TikTok Video'),
                                    'thumbnail': data['data'].get('cover'),
                                    'download_url': data['data'].get('play'),
                                    'author': data['data'].get('author', {}).get('unique_id')
                                }
                        elif api_url.startswith("https://api.tikmate"):
                            if data.get('video_url'):
                                if request.user:
                                    update_stats(request.user, platform)
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
                            if request.user:
                                update_stats(request.user, platform)
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
                        if request.user:
                            update_stats(request.user, platform)
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
                        if request.user:
                            update_stats(request.user, platform)
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
                        if request.user:
                            update_stats(request.user, platform)
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
                        if request.user:
                            update_stats(request.user, platform)
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
                original_url = url
                final_url = url
                
                if 'pin.it' in url:
                    try:
                        resp = await client.get(url, follow_redirects=True, timeout=15)
                        final_url = str(resp.url)
                    except:
                        pass
                
                pin_match = re.search(r'pin/(\d+)', final_url)
                if not pin_match:
                    pin_match = re.search(r'pinterest\.com/pin/(\d+)', final_url)
                
                if pin_match:
                    pin_id = pin_match.group(1)
                    
                    try:
                        resp = await client.get(
                            f"https://api.pinterest.com/v3/pidgets/pins/{pin_id}/",
                            timeout=15
                        )
                        data = resp.json()
                        if data.get('data'):
                            pin_data = data['data']
                            
                            if pin_data.get('image'):
                                img_url = pin_data['image'].get('original', {}).get('url')
                                if img_url:
                                    if request.user:
                                        update_stats(request.user, platform)
                                    return {
                                        'success': True,
                                        'title': pin_data.get('note', 'Pinterest Image'),
                                        'thumbnail': img_url,
                                        'download_url': img_url
                                    }
                            
                            if pin_data.get('video'):
                                video_url = pin_data['video'].get('url')
                                if video_url:
                                    if request.user:
                                        update_stats(request.user, platform)
                                    return {
                                        'success': True,
                                        'title': pin_data.get('note', 'Pinterest Video'),
                                        'thumbnail': pin_data.get('image', {}).get('original', {}).get('url'),
                                        'download_url': video_url
                                    }
                    except:
                        pass
                    
                    try:
                        resp = await client.get(f"https://pinterestdownloader.app/api/ajaxSearch?q={original_url}", timeout=15)
                        data = resp.json()
                        if data.get('video'):
                            if request.user:
                                update_stats(request.user, platform)
                            return {
                                'success': True,
                                'title': 'Pinterest Video',
                                'thumbnail': data.get('thumbnail'),
                                'download_url': data.get('video')
                            }
                        elif data.get('images') and len(data['images']) > 0:
                            img_url = data['images'][0] if isinstance(data['images'], list) else data['images'].get('orig', {}).get('url')
                            if request.user:
                                update_stats(request.user, platform)
                            return {
                                'success': True,
                                'title': 'Pinterest Image',
                                'thumbnail': data.get('thumbnail', img_url),
                                'download_url': img_url
                            }
                    except:
                        pass
                
                return {"success": False, "error": "Pinterest download failed"}
        
        else:
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

@app.get("/health")
def health():
    return {"status": "healthy"}