#!/bin/bash
echo "🚀 بدء تشغيل بوت MN.Py..."
echo "🔧 تثبيت المتطلبات الإضافية..."

# إنشاء مجلد مؤقت لتنزيل yt-dlp
mkdir -p temp_download
cd temp_download

# تنزيل yt-dlp مباشرة من GitHub
wget https://github.com/yt-dlp/yt-dlp/releases/download/2024.06.22/yt-dlp

# تثبيت yt-dlp يدويًا
chmod +x yt-dlp
sudo mv yt-dlp /usr/local/bin/yt-dlp

# العودة إلى المجلد الرئيسي
cd ..
rm -rf temp_download

# تثبيت باقي المتطلبات
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ تم تثبيت المتطلبات بنجاح"
python mn.py
