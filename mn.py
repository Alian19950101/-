#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import time
import re
import asyncio
import httpx
import atexit
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
import threading

# تحسينات الأداء والذاكرة لـ Render
threading.stack_size(256 * 1024 * 1024)  # 256MB stack size
os.environ['PYTHONUNBUFFERED'] = '1'

# إعدادات البوت
TOKEN = os.getenv('TOKEN', 'ضع_توكن_البوت_هنا')
BOT_USERNAME = "MN_Py_Bot"
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

# عميل HTTP محسن
http_client = httpx.AsyncClient(
    timeout=REQUEST_TIMEOUT,
    headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    },
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    http2=False,
    follow_redirects=True
)

atexit.register(lambda: asyncio.run(http_client.aclose()))

class BotUtils:
    @staticmethod
    def is_valid_url(url: str) -> bool:
        try:
            if not re.match(r'^https?://', url):
                url = 'https://' + url
            parsed = urlparse(url)
            if not parsed.netloc:
                return False
            supported = ['youtube.com', 'youtu.be', 'x.com', 'twitter.com', 'instagram.com', 'tiktok.com', 'facebook.com', 'fb.watch', 'vm.tiktok.com', 'twitch.tv', 'reddit.com', 'dailymotion.com', 'vimeo.com']
            return any(domain in parsed.netloc.lower() for domain in supported)
        except:
            return False

    @staticmethod
    def clean_url(url: str) -> str:
        url = re.sub(r'\s+', '', url)
        for param in ['?si=', '&feature=', '&t=', '&pp=', '&utm_', '&fbclid=']:
            if param in url:
                url = url.split(param)[0]
        return url.strip('/')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msg = (
        f"🚀 *مرحبًا {user.first_name}!*\n\n"
        "أنا *بوت MN.Py* لتحميل الفيديوهات من أي منصة!\n"
        "\n✅ أرسل رابط أي فيديو من المنصات المدعومة\n"
        "🌐 YouTube, Twitter, TikTok, Instagram, وغيرها\n"
        f"\n📌 الإصدار: 2.1\n🕒 التاريخ: {time.strftime('%Y-%m-%d')}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

def get_video_info_sync(url: str) -> dict:
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'ignoreerrors': True,
            'noplaylist': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0'
            }
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            return {
                'title': info.get('title', 'لا عنوان'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration', 0),
                'url': info.get('webpage_url', url),
                'uploader': info.get('uploader', 'غير معروف')
            }
    except:
        return None

async def download_video_async(url: str) -> str:
    try:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'retries': 3
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except:
        return None

async def handle_video_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with download_semaphore:
        url = BotUtils.clean_url(update.message.text.strip())
        if not BotUtils.is_valid_url(url):
            await update.message.reply_text("⚠️ الرابط غير مدعوم أو غير صالح.")
            return

        msg = await update.message.reply_text("🔍 جاري التحليل...")
        info = await asyncio.get_running_loop().run_in_executor(None, get_video_info_sync, url)
        if not info:
            await msg.edit_text("❌ تعذر جلب معلومات الفيديو.")
            return

        await msg.edit_text("📥 جاري التحميل...")
        file_path = await download_video_async(url)
        if not file_path or not os.path.exists(file_path):
            await msg.edit_text("❌ فشل في تحميل الفيديو.")
            return

        try:
            await update.message.reply_video(
                video=open(file_path, 'rb'),
                caption=f"🎬 {info['title']}\n📤 بواسطة @{BOT_USERNAME}",
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text("⚠️ تعذر إرسال الفيديو.")
        finally:
            os.remove(file_path)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"خطأ: {context.error}")
    if update and update.message:
        await update.message.reply_text("⚠️ حدث خطأ غير متوقع. حاول لاحقًا.")

def cleanup_downloads():
    for f in os.listdir(DOWNLOAD_FOLDER):
        try:
            path = os.path.join(DOWNLOAD_FOLDER, f)
            if os.path.isfile(path):
                os.remove(path)
        except:
            continue

async def main():
    cleanup_downloads()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_url))
    app.add_error_handler(error_handler)
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
