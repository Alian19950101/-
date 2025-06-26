#!/bin/bash
echo "🚀 بدء تشغيل بوت MN.Py..."
echo "🔧 تثبيت المتطلبات الإضافية..."

# تثبيت المتطلبات الأساسية
pip install --upgrade pip
pip install python-telegram-bot[ext]==20.6 httpx==0.27.0 aiohttp==3.9.5 pyyaml==6.0.1

# تثبيت yt-dlp من المصدر الصحيح
pip install git+https://github.com/yt-dlp/yt-dlp.git@2024.06.22

# تنظيف ذاكرة التخزين المؤقت
rm -rf ~/.cache/pip

echo "✅ تم تثبيت المتطلبات بنجاح"
python mn.py
