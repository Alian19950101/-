#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import time
import re
import asyncio
import httpx
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
import yt_dlp as youtube_dl
from yt_dlp.utils import DownloadError

# تحسينات الأداء والذاكرة لـ Render
import threading
threading.stack_size(256 * 1024 * 1024)  # 256MB stack size
os.environ['PYTHONUNBUFFERED'] = '1'

# إعدادات البوت
TOKEN = os.getenv('TOKEN', '7872075207:AAHy75gQAHyTFxIs0lg5Eu7MhiDckV6_2ak')
BOT_USERNAME = "MN.Py"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_RETRIES = 3
REQUEST_TIMEOUT = 45
MAX_CONCURRENT_DOWNLOADS = 2

# إعدادات متقدمة للتسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# مجلد التنزيلات
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "MN_Py_Downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# قائمة الانتظار للتحميلات المتزامنة
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

# عميل HTTP محسن - تم تعطيل HTTP/2 هنا
http_client = httpx.AsyncClient(
    timeout=REQUEST_TIMEOUT,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    },
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    http2=False,  # تم تعطيل HTTP/2 هنا
    follow_redirects=True
)

class BotUtils:
    """فئة مساعدة للوظائف المشتركة"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """تحقق من صحة الرابط مع دعم إضافي"""
        try:
            if not re.match(r'^https?://', url):
                url = 'https://' + url
            
            parsed = urlparse(url)
            if not parsed.netloc:
                return False
                
            supported_domains = [
                'youtube.com', 'youtu.be', 
                'twitter.com', 'x.com',
                'instagram.com', 'tiktok.com',
                'facebook.com', 'fb.watch',
                'vm.tiktok.com', 'www.tiktok.com',
                'www.instagram.com', 'www.facebook.com',
                'fb.com', 'm.facebook.com',
                'twitch.tv', 'reddit.com',
                'dailymotion.com', 'vimeo.com'
            ]
            
            return any(domain in parsed.netloc.lower() for domain in supported_domains)
        except:
            return False
    
    @staticmethod
    def clean_url(url: str) -> str:
        """تنظيف الرابط من المعلمات الزائدة"""
        url = re.sub(r'\s+', '', url)
        
        # إزالة المعلمات الشائعة
        params_to_remove = ['?si=', '&feature=', '&t=', '&pp=', '&utm_', '&fbclid=']
        for param in params_to_remove:
            if param in url:
                url = url.split(param)[0]
        
        return url.strip('/')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """رسالة ترحيبية متطورة مع إرشادات استخدام"""
    user = update.effective_user
    help_text = (
        f"🚀 *مرحبًا {user.first_name}!* 🚀\n\n"
        "أنا *بوت MN.Py* المتكامل لتحميل الفيديوهات من أي منصة!\n\n"
        "✅ *المميزات:*\n"
        "- ⚡ تنزيل فائق السرعة\n"
        "- 🌐 يدعم +15 منصة (يوتيوب، تويتر، تيك توك، إنستجرام...)\n"
        "- 💯 يعمل 24/7 على Render\n\n"
        "📌 *كيفية الاستخدام:*\n"
        "1. أرسل رابط الفيديو مباشرة\n"
        "2. انتظر حتى يتم التحليل والتحميل\n"
        "3. استلم الفيديو بأفضل جودة متاحة\n\n"
        "⚙️ *معلومات تقنية:*\n"
        f"- الإصدار: 2.1 (مخصص لـ Render)\n"
        f"- حالة الخدمة: نشط ✅\n"
        f"- آخر تحديث: {time.strftime('%Y-%m-%d')}"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

def get_video_info_sync(url: str) -> dict:
    """الحصول على معلومات الفيديو مع معالجة محسنة للأخطاء"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'ignoreerrors': True,
            'noplaylist': True,
            'cookiefile': None,
            'extract_flat': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.google.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1'
            }
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.error("فشل في جلب معلومات الفيديو")
                return None
            
            # معالجة المدة
            duration = info.get('duration', 0)
            duration_str = "غير معروف"
            if duration and duration > 0:
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = int(duration % 60)
                if hours > 0:
                    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"{minutes}:{seconds:02d}"
            
            # معالجة الصورة المصغرة
            thumbnail = info.get('thumbnail', '')
            if not thumbnail and 'thumbnails' in info:
                thumbnails = info['thumbnails']
                if thumbnails:
                    thumbnail = sorted(
                        thumbnails, 
                        key=lambda x: x.get('width', 0), 
                        reverse=True
                    )[0]['url']
            
            # معالجة العنوان
            title = (info.get('title') or info.get('description') or url.split('/')[-1])
            title = re.sub(r'[^\w\s-]', '', title)[:100].strip()
            
            return {
                'title': title or "فيديو بدون عنوان",
                'thumbnail': thumbnail,
                'duration': duration_str,
                'url': url,
                'webpage_url': info.get('webpage_url', url),
                'uploader': info.get('uploader', 'غير معروف')
            }
    except DownloadError as e:
        logger.error(f"خطأ في yt-dlp: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"خطأ غير متوقع في get_video_info: {str(e)}")
        return None

async def download_video_async(url: str) -> str:
    """تنزيل الفيديو مع إدارة الذاكرة"""
    try:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 60,
            'retries': 3,
            'ignoreerrors': True,
            'noplaylist': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.google.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1'
            },
            'buffersize': 65536,  # تحسين للأداء
            'noresizebuffer': True,
            'extractaudio': False,
            'keepvideo': True
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        
        return file_path
    except Exception as e:
        logger.error(f"خطأ في التنزيل: {str(e)}")
        return None

async def handle_video_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة رابط الفيديو مع تحسينات للاستقرار"""
    async with download_semaphore:
        url = update.message.text.strip()
        url = BotUtils.clean_url(url)
        
        if not BotUtils.is_valid_url(url):
            platforms = [
                "يوتيوب (youtube.com, youtu.be)",
                "تويتر (twitter.com, x.com)",
                "إنستجرام (instagram.com)",
                "تيك توك (tiktok.com, vm.tiktok.com)",
                "فيسبوك (facebook.com, fb.watch)"
            ]
            platforms_text = "\n- ".join(platforms)
            
            await update.message.reply_text(
                f"⚠️ *الرابط غير مدعوم*\n\n"
                f"المنصات المدعومة:\n"
                f"- {platforms_text}\n\n"
                "📌 تأكد من:\n"
                "1. أن الرابط يبدأ بـ http:// أو https://\n"
                "2. أن الفيديو ليس خاصًا أو محميًا بكلمة مرور",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            return
        
        processing_msg = await update.message.reply_text(
            "⚡ جاري تحليل الرابط...",
            reply_to_message_id=update.message.message_id
        )
        
        try:
            loop = asyncio.get_running_loop()
            video_info = None
            
            # محاولات متعددة للحصول على معلومات الفيديو
            for attempt in range(MAX_RETRIES):
                try:
                    video_info = await loop.run_in_executor(
                        None, 
                        get_video_info_sync, 
                        url
                    )
                    if video_info:
                        break
                    await asyncio.sleep(1 + attempt)  # زيادة التأخير مع كل محاولة
                except Exception as e:
                    logger.warning(f"المحاولة {attempt + 1} فشلت: {str(e)}")
                    if attempt == MAX_RETRIES - 1:
                        raise
            
            if not video_info:
                await processing_msg.edit_text(
                    "❌ *تعذر تحليل الفيديو*\n\n"
                    "قد يكون السبب:\n"
                    "1. الرابط غير صحيح\n"
                    "2. الفيديو محذوف أو خاص\n"
                    "3. مشكلة في الخادم\n\n"
                    "جرب رابطًا آخر أو حاول لاحقًا",
                    parse_mode="Markdown"
                )
                return
            
            # إعداد رسالة المعلومات
            caption = (
                f"🎬 *{video_info['title']}*\n"
                f"🕒 المدة: {video_info['duration']}\n"
                f"📤 رفع بواسطة: {video_info['uploader']}\n\n"
                "⚡ جاري التحميل بأفضل جودة متاحة..."
            )
            
            # إرسال الصورة المصغرة إذا وجدت
            if video_info.get('thumbnail'):
                try:
                    await update.message.reply_photo(
                        photo=video_info['thumbnail'],
                        caption=caption,
                        parse_mode="Markdown",
                        reply_to_message_id=update.message.message_id
                    )
                except Exception as e:
                    logger.warning(f"فشل إرسال الصورة المصغرة: {str(e)}")
            
            await processing_msg.edit_text("⚡ جاري تحميل الفيديو...")
            start_time = time.time()
            
            # تنزيل الفيديو
            file_path = await download_video_async(url)
            
            if not file_path or not os.path.exists(file_path):
                await processing_msg.edit_text("❌ فشل في تحميل الفيديو")
                return
            
            download_time = time.time() - start_time
            await processing_msg.edit_text(
                f"✅ تم التحميل بنجاح في {download_time:.1f} ثانية\n"
                f"📦 جاري إعداد الفيديو للإرسال..."
            )
            
            # إرسال الفيديو
            await send_video_to_user(update, context, file_path, video_info)
            
        except Exception as e:
            logger.error(f"خطأ رئيسي في handle_video_url: {str(e)}", exc_info=True)
            await processing_msg.edit_text(
                "⚠️ حدث خطأ غير متوقع\n"
                "جاري إعادة التشغيل التلقائي...\n"
                "يمكنك المحاولة مرة أخرى بعد قليل"
            )
            # إعادة تشغيل البوت بعد خطأ فادح
            os.execv(sys.executable, ['python'] + sys.argv)

async def send_video_to_user(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    file_path: str, 
    video_info: dict
):
    """إرسال الفيديو للمستخدم مع معالجة متقدمة للأخطاء"""
    try:
        file_size = os.path.getsize(file_path)
        duration = video_info.get('duration', 'غير معروف')
        title = video_info.get('title', 'فيديو')
        
        # إعداد التسمية التوضيحية
        caption = (
            f"🎬 *{title}*\n"
            f"🕒 المدة: {duration}\n"
            f"📤 تم التحميل بواسطة @{BOT_USERNAME}"
        )
        
        # إرسال الفيديو أو الملف حسب الحجم
        if file_size > MAX_FILE_SIZE:
            await update.message.reply_document(
                document=open(file_path, 'rb'),
                caption=caption,
                parse_mode="Markdown",
                thumb=video_info.get('thumbnail'),
                timeout=120,
                reply_to_message_id=update.message.message_id
            )
        else:
            await update.message.reply_video(
                video=open(file_path, 'rb'),
                caption=caption,
                parse_mode="Markdown",
                duration=video_info.get('duration_seconds'),
                thumb=video_info.get('thumbnail'),
                supports_streaming=True,
                timeout=120,
                reply_to_message_id=update.message.message_id
            )
            
    except Exception as e:
        logger.error(f"خطأ في إرسال الفيديو: {str(e)}")
        await update.message.reply_text(
            "⚠️ تعذر إرسال الفيديو بسبب:\n"
            f"- الحجم: {file_size // (1024 * 1024)}MB\n"
            "- قد يكون الحجم أكبر من المسموح به في التليجرام\n\n"
            "يمكنك:\n"
            "1. طلب نسخة أصغر\n"
            "2. تجربة رابط آخر",
            reply_to_message_id=update.message.message_id
        )
    finally:
        # تنظيف الملف المؤقت
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"خطأ في حذف الملف: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الأخطاء مع إعادة تشغيل تلقائية"""
    error = context.error
    logger.error(f"حدث خطأ: {str(error)}", exc_info=True)
    
    if update and update.message:
        try:
            await update.message.reply_text(
                "🔧 حدث خطأ غير متوقع\n"
                "جاري إعادة التشغيل التلقائي...\n"
                "يمكنك المحاولة مرة أخرى بعد قليل",
                reply_to_message_id=update.message.message_id
            )
        except Exception as e:
            logger.error(f"فشل في إرسال رسالة الخطأ: {str(e)}")
    
    # إعادة التشغيل بعد 10 ثواني
    await asyncio.sleep(10)
    os.execv(sys.executable, ['python'] + sys.argv)

def cleanup_resources():
    """تنظيف الموارد قبل التشغيل"""
    try:
        # تنظيف مجلد التنزيلات
        for filename in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"فشل في حذف {filename}: {str(e)}")
        
        # إغلاق عميل HTTP
        try:
            asyncio.get_event_loop().run_until_complete(http_client.aclose())
        except:
            pass
            
    except Exception as e:
        logger.error(f"خطأ في تنظيف الموارد: {str(e)}")

def main() -> None:
    """الدالة الرئيسية مع تحسينات للاستقرار"""
    cleanup_resources()
    
    try:
        # إعداد التطبيق مع تحسينات
        app = Application.builder().token(TOKEN).build()
        
        # تسجيل المعالجات
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_url))
        app.add_error_handler(error_handler)
        
        # تشغيل البوت مع إعدادات محسنة
        app.run_polling(
            poll_interval=1.5,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
            stop_signals=[]
        )
    except Exception as e:
        logger.critical(f"خطأ فادح في التشغيل: {str(e)}")
        # إعادة التشغيل بعد 30 ثانية
        time.sleep(30)
        os.execv(sys.executable, ['python'] + sys.argv)

if __name__ == '__main__':
    # تشغيل البوت مع استعادة من الأخطاء
    while True:
        try:
            main()
        except KeyboardInterrupt:
            logger.info("إيقاف البوت بواسطة المستخدم")
            break
        except Exception as e:
            logger.critical(f"إعادة التشغيل بسبب: {str(e)}")
            time.sleep(10)
            continue
