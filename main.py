from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
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
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # ========== يوتيوب ==========
            if platform == 'youtube':
                # استخدام y2mate
                resp = await client.get(f"https://y2mate.is/api/json?url={url}")
                data = resp.json()
                if data.get('video', {}).get('url'):
                    return {
                        'success': True,
                        'title': data.get('title', 'YouTube Video'),
                        'thumbnail': data.get('thumbnail'),
                        'download_url': data['video']['url']
                    }
            
            # ========== تيك توك (شغال) ==========
            elif platform == 'tiktok':
                # TikWM API
                resp = await client.get(f"https://tikwm.com/api/?url={url}")
                data = resp.json()
                if data.get('code') == 0:
                    return {
                        'success': True,
                        'title': data['data'].get('title', 'TikTok Video'),
                        'thumbnail': data['data'].get('cover'),
                        'download_url': data['data'].get('play'),
                        'author': data['data'].get('author', {}).get('unique_id')
                    }
            
            # ========== انستقرام (شغال) ==========
            elif platform == 'instagram':
                # Instagram Downloader API
                resp = await client.get(f"https://instagramdl.hitesh-01.repl.co/instagram?url={url}")
                data = resp.json()
                if data.get('result'):
                    result = data['result']
                    download_url = result.get('video_url')
                    if not download_url and result.get('images'):
                        download_url = result['images'][0] if result['images'] else None
                    return {
                        'success': True,
                        'title': 'Instagram Post',
                        'thumbnail': result.get('thumbnail'),
                        'download_url': download_url
                    }
            
            # ========== فيسبوك (شغال) ==========
            elif platform == 'facebook':
                # FBDown API
                resp = await client.get(f"https://fbdown.net/api/ajaxSearch?q={url}")
                data = resp.json()
                if data.get('links'):
                    return {
                        'success': True,
                        'title': 'Facebook Video',
                        'thumbnail': data.get('thumbnail'),
                        'download_url': data['links'].get('Download High Quality') or data['links'].get('Download Low Quality')
                    }
            
            # ========== تويتر (شغال) ==========
            elif platform == 'twitter':
                # Twitsave API
                resp = await client.post(
                    "https://twitsave.com/api/ajaxSearch",
                    data={'q': url},
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
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
            
            # ========== سبوتيفاي (شغال) ==========
            elif platform == 'spotify':
                track_match = re.search(r'track/([a-zA-Z0-9]+)', url)
                if track_match:
                    resp = await client.get(f"https://api.spotifydown.com/download/{track_match.group(1)}")
                    data = resp.json()
                    if data.get('link'):
                        return {
                            'success': True,
                            'title': data.get('title'),
                            'thumbnail': data.get('thumbnail'),
                            'download_url': data.get('link'),
                            'author': data.get('artist')
                        }
            
            # ========== بينترست (شغال) ==========
            elif platform == 'pinterest':
                resp = await client.get(f"https://pinterestdownloader.app/api/ajaxSearch?q={url}")
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
            
            return {'success': False, 'error': f'المنصة {platform} غير مدعومة أو الرابط غير صالح'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Downloader API v8 - يدعم جميع المنصات",
        "platforms": ["youtube", "tiktok", "instagram", "facebook", "twitter", "spotify", "pinterest"]
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
