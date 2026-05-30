from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re
import httpx
import json
import os
from typing import Optional
from datetime import datetime
import hashlib
import secrets

app = FastAPI(title="Downloader API")

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

def update_settings(platform: str, enabled: bool):
    settings = get_settings()
    settings[platform] = enabled
    save_json(SETTINGS_FILE, settings)
    return settings

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

class AdminRequest(BaseModel):
    password: str

class PlatformToggleRequest(BaseModel):
    platform: str
    enabled: bool
    password: str

# ========== دوال المستخدمين ==========
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username: str, password: str):
    users = load_json(USERS_FILE)
    if username in users:
        return False, "اسم المستخدم موجود بالفعل"
    
    users[username] = {
        "password": hash_password(password),
        "created_at": datetime.now().isoformat(),
        "downloads": 0
    }
    save_json(USERS_FILE, users)
    return True, "تم إنشاء الحساب"

def login_user(username: str, password: str):
    users = load_json(USERS_FILE)
    if username not in users:
        return False, "اسم المستخدم غير موجود"
    
    if users[username]["password"] != hash_password(password):
        return False, "كلمة المرور غير صحيحة"
    
    return True, users[username]

# ========== إحصائيات ==========
def update_stats(username: str, platform: str):
    stats = load_json(STATS_FILE)
    
    # إحصائيات عامة
    if "total_downloads" not in stats:
        stats["total_downloads"] = 0
    stats["total_downloads"] += 1
    
    # إحصائيات المنصات
    if "platforms" not in stats:
        stats["platforms"] = {}
    if platform not in stats["platforms"]:
        stats["platforms"][platform] = 0
    stats["platforms"][platform] += 1
    
    # إحصائيات المستخدمين
    if "users" not in stats:
        stats["users"] = {}
    if username not in stats["users"]:
        stats["users"][username] = 0
    stats["users"][username] += 1
    
    # آخر تحميل
    stats["last_download"] = datetime.now().isoformat()
    
    save_json(STATS_FILE, stats)
    
    # تحديث عدد تحميلات المستخدم
    users = load_json(USERS_FILE)
    if username in users:
        users[username]["downloads"] = stats["users"][username]
        save_json(USERS_FILE, users)

def get_stats():
    stats = load_json(STATS_FILE)
    users = load_json(USERS_FILE)
    
    return {
        "total_downloads": stats.get("total_downloads", 0),
        "total_users": len(users),
        "platforms": stats.get("platforms", {}),
        "top_users": sorted(stats.get("users", {}).items(), key=lambda x: x[1], reverse=True)[:5],
        "last_download": stats.get("last_download")
    }

# ========== reCAPTCHA (اختياري) ==========
async def verify_recaptcha(token: str):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": "YOUR_SECRET_KEY", "response": token}
            )
            return resp.json().get("success", False)
    except:
        return True  # إذا فشل التحقق، نسمح مؤقتاً

# ========== دالة التحميل ==========
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
    elif 'pinterest.com' in url_lower or 'pin.it' in url_lower:
        return 'pinterest'
    else:
        return 'other'

async def process_download(url: str, media_type: str):
    platform = detect_platform(url)
    settings = get_settings()
    
    # التحقق إذا كانت المنصة مفعلة
    if not settings.get(platform, True):
        return {'success': False, 'error': f'❌ منصة {platform} معطلة حالياً من قبل المطور'}
    
    if platform == 'youtube':
        if media_type == 'audio':
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
                'author': info.get('uploader')
            }
    
    elif platform == 'tiktok':
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://tikwm.com/api/?url={url}")
            data = resp.json()
            if data.get('code') == 0:
                return {
                    'success': True,
                    'title': data['data'].get('title'),
                    'thumbnail': data['data'].get('cover'),
                    'download_url': data['data'].get('play')
                }
    
    elif platform == 'instagram':
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"https://instagramdl.hitesh-01.repl.co/instagram?url={url}")
                data = resp.json()
                if data.get('result'):
                    result = data['result']
                    download_url = result.get('video_url') or (result.get('images', [''])[0] if result.get('images') else None)
                    return {
                        'success': True,
                        'title': result.get('title', 'Instagram'),
                        'thumbnail': result.get('thumbnail'),
                        'download_url': download_url
                    }
            except:
                pass
    
    elif platform == 'facebook':
        async with httpx.AsyncClient() as client:
            try:
                ydl_opts = {'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return {
                        'success': True,
                        'title': info.get('title'),
                        'thumbnail': info.get('thumbnail'),
                        'download_url': info.get('url')
                    }
            except:
                pass
    
    elif platform == 'twitter':
        async with httpx.AsyncClient() as client:
            try:
                ydl_opts = {'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return {
                        'success': True,
                        'title': info.get('title'),
                        'thumbnail': info.get('thumbnail'),
                        'download_url': info.get('url')
                    }
            except:
                pass
    
    elif platform == 'spotify':
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"https://api.evogb.org/dl/spotify?url={url}&key=sasuke")
                data = resp.json()
                if data.get("status"):
                    info = data.get("data", {})
                    return {
                        'success': True,
                        'title': info.get("name"),
                        'thumbnail': info.get("imageHD"),
                        'download_url': info.get("url"),
                        'author': info.get("artist")
                    }
            except:
                pass
    
    elif platform == 'pinterest':
        pin_match = re.search(r'pin/(\d+)', url)
        if pin_match:
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(f"https://api.pinterest.com/v3/pidgets/pins/{pin_match.group(1)}/")
                    data = resp.json()
                    if data.get('data'):
                        pin_data = data['data']
                        if pin_data.get('image'):
                            return {
                                'success': True,
                                'title': pin_data.get('note', 'Pinterest'),
                                'thumbnail': pin_data['image'].get('original', {}).get('url'),
                                'download_url': pin_data['image']['original']['url']
                            }
                except:
                    pass
    
    return {'success': False, 'error': f'فشل تحميل من {platform}'}

# ========== API Endpoints ==========

@app.post("/register")
async def register(request: RegisterRequest):
    success, message = register_user(request.username, request.password)
    if success:
        return {"success": True, "message": message}
    return {"success": False, "error": message}

@app.post("/login")
async def login(request: LoginRequest):
    success, data = login_user(request.username, request.password)
    if success:
        return {"success": True, "user": request.username, "downloads": data.get("downloads", 0)}
    return {"success": False, "error": data}

@app.post("/download")
async def download(request: DownloadRequest):
    result = await process_download(request.url, request.type)
    
    if result.get('success') and request.user:
        platform = detect_platform(request.url)
        update_stats(request.user, platform)
    
    return result

@app.post("/admin/stats")
async def admin_stats(request: AdminRequest):
    if request.password != "s7abow":
        return {"success": False, "error": "كلمة المرور غير صحيحة"}
    return {"success": True, "stats": get_stats()}

@app.post("/admin/settings")
async def admin_settings(request: PlatformToggleRequest):
    if request.password != "s7abow":
        return {"success": False, "error": "كلمة المرور غير صحيحة"}
    
    settings = update_settings(request.platform, request.enabled)
    return {"success": True, "settings": settings}

@app.get("/admin/settings")
async def get_admin_settings():
    return {"success": True, "settings": get_settings()}

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Downloader API v2",
        "platforms": list(get_settings().keys())
    }

@app.get("/health")
def health():
    return {"status": "healthy"}