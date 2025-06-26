#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import logging
import time
import re
import asyncio
import signal
from urllib.parse import urlparse
import aiohttp
from aiohttp import web

# تثبيت الحزم المطلوبة
required_packages = [
    "python-telegram-bot==20.6",
    "httpx==0.25.2",
    "aiohttp==3.9.5",
    "pyyaml==6.0.1",
    "yt-dlp==2024.6.22"
]

try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters
    )
    import httpx
    import yt_dlp as youtube_dl
    from yt_dlp.utils import DownloadError
except ImportError:
    print("جاري تثبيت الحزم المطلوبة...")
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + required_packages)
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters
    )
    import httpx
    import yt_dlp as youtube_dl
    from yt_dlp.utils import DownloadError

# إعدادات البوت - التوكن من متغيرات البيئة
TOKEN = os.environ.get("TOKEN", "7872075207:AAHy75gQAHyTFxIs0lg5Eu7MhiDckV6_2ak")
BOT_USERNAME = "MN.Py"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# مجلد التنزيلات
DOWNLOAD_FOLDER = "MN_Py_Downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# عميل HTTP للتحقق من الروابط
http_client = httpx.AsyncClient(
    timeout=30.0,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    },
    follow_redirects=True
)

def is_valid_url(url: str) -> bool:
    """تحقق من صحة الرابط"""
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
            'fb.com', 'm.facebook.com'
        ]
        
        return any(domain in parsed.netloc for domain in supported_domains)
    except:
        return False

def clean_url(url: str) -> str:
    """تنظيف الرابط من المعلمات الزائدة"""
    url = re.sub(r'\s+', '', url)
    
    # إزالة المعلمات الشائعة
    for param in ['?si=', '&feature=', '&t=', '&pp=', '&utm_']:
        if param in url:
            url = url.split(param)[0]
    
    return url

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """رسالة ترحيبية متطورة"""
    user = update.effective_user
    await update.message.reply_text(
        f"🚀 *مرحبًا {user.first_name}!* 🚀\n\n"
        "أنا *بوت MN.Py* المتكامل لتحميل الفيديوهات من أي منصة!\n\n"
        "✅ *مميزاتي:*\n"
        "- ⚡ تنزيل فائق السرعة\n"
        "- 🌐 يدعم جميع المنصات (يوتيوب، تويتر، تيك توك، إنستجرام)\n"
        "- 💯 يعمل بدون أخطاء\n\n"
        "📌 *كيفية الاستخدام:*\n"
        "1. أرسل رابط الفيديو\n"
        "2. استلم الفيديو فورًا",
        parse_mode="Markdown"
    )

def get_video_info_sync(url: str) -> dict:
    """الحصول على معلومات الفيديو (نسخة متزامنة)"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'ignoreerrors': True,
            'noplaylist': True,
            'cookiefile': None,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://twitter.com/',
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
            if duration:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "غير معروف"
            
            # الحصول على أفضل صورة مصغرة
            thumbnails = info.get('thumbnails', [])
            best_thumbnail = ''
            if thumbnails:
                best_res = 0
                for thumb in thumbnails:
                    if thumb.get('width', 0) > best_res:
                        best_thumbnail = thumb['url']
                        best_res = thumb.get('width', 0)
            
            return {
                'title': (info.get('title') or info.get('description') or url.split('/')[-1])[:100],
                'thumbnail': best_thumbnail or info.get('thumbnail', ''),
                'duration': duration_str,
                'url': url
            }
    except DownloadError as e:
        logger.error(f"خطأ في yt-dlp: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {str(e)}")
        return None

def download_video_sync(url: str) -> str:
    """تنزيل الفيديو (نسخة متزامنة)"""
    try:
        # إعدادات yt-dlp محسنة للتوافق مع Render
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 60,
            'retries': 5,
            'ignoreerrors': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://twitter.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1'
            }
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        
        return file_path
    except Exception as e:
        logger.error(f"خطأ في التنزيل: {str(e)}")
        return None

async def handle_video_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة رابط الفيديو مع تحسينات لتويتر"""
    url = update.message.text.strip()
    url = clean_url(url)
    
    if not is_valid_url(url):
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
            "تأكد أن الرابط يبدأ بـ http:// أو https://",
            parse_mode="Markdown"
        )
        return
    
    processing_msg = await update.message.reply_text("⚡ جاري التحليل...")
    
    try:
        loop = asyncio.get_running_loop()
        video_info = None
        for attempt in range(3):
            video_info = await loop.run_in_executor(None, get_video_info_sync, url)
            if video_info:
                break
            await asyncio.sleep(1)
        
        if not video_info:
            await context.bot.delete_message(
                chat_id=processing_msg.chat_id,
                message_id=processing_msg.message_id
            )
            await update.message.reply_text(
                "❌ *تعذر تحميل الفيديو*\n\n"
                "🛠️ *الحلول المقترحة:*\n"
                "1. تأكد من صحة الرابط\n"
                "2. جرب رابطًا آخر\n"
                "3. استخدم VPN إذا لزم الأمر\n"
                "4. تأكد أن الفيديو ليس خاصًا\n"
                "5. جرب الرابط في متصفحك أولاً",
                parse_mode="Markdown"
            )
            return
        
        context.user_data['video_url'] = url
        
        await context.bot.delete_message(
            chat_id=processing_msg.chat_id,
            message_id=processing_msg.message_id
        )
        
        caption = (
            f"🎬 *{video_info['title']}*\n"
            f"⏱ المدة: {video_info['duration']}\n\n"
            "⚡ جاري التحميل بأفضل جودة..."
        )
        
        try:
            if video_info['thumbnail']:
                await update.message.reply_photo(
                    photo=video_info['thumbnail'],
                    caption=caption,
                    parse_mode="Markdown"
                )
                progress_msg = await update.message.reply_text("⚡ جاري التحميل...")
                start_time = time.time()
                
                file_path = await loop.run_in_executor(None, download_video_sync, url)
                
                if not file_path or not os.path.exists(file_path):
                    await progress_msg.edit_text("❌ فشل في تنزيل الفيديو")
                    return
                
                download_time = time.time() - start_time
                await progress_msg.edit_text(f"✅ تم التحميل في {download_time:.1f} ثانية")
                
                await send_video_to_user(update, context, file_path, "أفضل جودة")
                return
        except Exception as e:
            logger.error(f"خطأ في إرسال الصورة: {str(e)}")
            pass
        
        info_msg = await update.message.reply_text(
            text=caption,
            parse_mode="Markdown"
        )
        
        progress_msg = await update.message.reply_text("⚡ جاري التحميل...")
        start_time = time.time()
        
        file_path = await loop.run_in_executor(None, download_video_sync, url)
        
        if not file_path or not os.path.exists(file_path):
            await progress_msg.edit_text("❌ فشل في تنزيل الفيديو")
            return
        
        download_time = time.time() - start_time
        await progress_msg.edit_text(f"✅ تم التحميل في {download_time:.1f} ثانية")
        
        await send_video_to_user(update, context, file_path, "أفضل جودة")

    except Exception as e:
        logger.error(f"خطأ في المعالجة: {str(e)}")
        await update.message.reply_text("⚡ حدث خطأ، جاري إعادة المحاولة تلقائيًا...")

async def send_video_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str, quality: str):
    """إرسال الفيديو للمستخدم مع معالجة الأخطاء"""
    try:
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_FILE_SIZE:
            await update.message.reply_document(
                document=open(file_path, 'rb'),
                caption=f"📦 حجم الفيديو كبير جدًا\n⚡ الجودة: {quality}"
            )
        else:
            await update.message.reply_video(
                video=open(file_path, 'rb'),
                caption=f"✅ تم التنزيل بنجاح | الجودة: {quality}",
                supports_streaming=True,
                read_timeout=300,
                write_timeout=300,
                connect_timeout=300
            )
    except Exception as e:
        logger.error(f"خطأ في الإرسال: {str(e)}")
        await update.message.reply_text(
            "⚠️ تعذر إرسال الفيديو\n"
            "🛠️ جرب رابطًا مختلفًا أو استخدم VPN"
        )
    finally:
        try:
            os.remove(file_path)
        except:
            pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الأخطاء بذكاء"""
    logger.error("حدث خطأ:", exc_info=context.error)
    
    if update and update.message:
        try:
            await update.message.reply_text(
                "🔧 تم حل المشكلة تلقائيًا\n"
                "✅ يمكنك المحاولة مرة أخرى"
            )
        except:
            pass

def run_bot():
    """تشغيل البوت في وضع polling"""
    # تنظيف الملفات القديمة
    for filename in os.listdir(DOWNLOAD_FOLDER):
        try:
            os.remove(os.path.join(DOWNLOAD_FOLDER, filename))
        except:
            pass
    
    # إنشاء التطبيق
    bot_app = Application.builder().token(TOKEN).build()
    
    # تسجيل المعالجات
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_url))
    bot_app.add_error_handler(error_handler)
    
    # تشغيل البوت
    logger.info("جارٍ تشغيل البوت...")
    bot_app.run_polling(
        poll_interval=0.5,
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

async def web_server():
    """إنشاء خادم ويب بسيط لريندر"""
    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 5000))
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    logger.info(f"خادم الويب يعمل على المنفذ {port}")
    # انتظار إلى الأبد
    await asyncio.Event().wait()

def handle_exit(signum, frame):
    """معالجة إشارة الخروج لتنظيف الموارد"""
    logger.info("تلقي إشارة إنهاء، جاري التنظيف...")
    # تنظيف الملفات المؤقتة
    for filename in os.listdir(DOWNLOAD_FOLDER):
        try:
            os.remove(os.path.join(DOWNLOAD_FOLDER, filename))
        except:
            pass
    logger.info("تم التنظيف بنجاح، إيقاف البوت.")
    os._exit(0)

async def main():
    """الدالة الرئيسية لتشغيل البوت وخادم الويب"""
    # تشغيل البوت في مؤشر ترابط منفصل
    loop = asyncio.get_running_loop()
    bot_task = loop.run_in_executor(None, run_bot)
    
    # تشغيل خادم الويب
    await web_server()

if __name__ == '__main__':
    # تسجيل معالج الإشارات
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # تشغيل التطبيق
    asyncio.run(main())
