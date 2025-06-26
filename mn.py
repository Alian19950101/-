#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
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

# تحسين الأداء لـ Render
import threading
threading.stack_size(200 * 1024 * 1024)  # 200MB stack size

# إعدادات البوت (يُفضل استخدام متغيرات البيئة)
TOKEN = os.getenv('TOKEN', '7872075207:AAHy75gQAHyTFxIs0lg5Eu7MhiDckV6_2ak')
BOT_USERNAME = "MN.Py"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_RETRIES = 3  # عدد المحاولات عند الفشل
REQUEST_TIMEOUT = 30  # ثانية

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
    timeout=REQUEST_TIMEOUT,
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
        "أنا *بوت MN.Py* المتكامل لتحميل الفيديوهات من أي منصة!\n
