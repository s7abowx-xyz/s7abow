from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
from typing import Optional

app = FastAPI(title="Downloader API")

# إعدادات CORS (ضروري لاتصال موقعك بالـ API)
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

# دالة تحميل واحدة وموحدة لكل شيء
def download_with_ytdlp(url: str, is_audio: bool = False):
    # إعدادات yt-dlp
    if is_audio:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
        }
    else:
        ydl_opts = {
            'format': 'best[height<=720]',  # جودة ممتازة وحجم مناسب
            'quiet': True,
            'no_warnings': True,
        }
    
    # استخراج المعلومات والحصول على رابط التحميل المباشر
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
    try:
        # استدعاء دالة التحميل لكل الروابط (يوتيوب، تيك توك، فيسبوك، الخ)
        result = download_with_ytdlp(request.url, request.type == 'audio')
        return result
    except Exception as e:
        # في حالة حدوث خطأ، نعيد رسالة واضحة
        return {'success': False, 'error': f'حدث خطأ: {str(e)}'}

@app.get("/")
def root():
    return {"status": "ok", "message": "Downloader API - يدعم جميع المنصات (YouTube, TikTok, Instagram, Facebook, Twitter, Pinterest, وغيرها)"}
