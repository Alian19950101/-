import os
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# توكن البوت
BOT_TOKEN = "7872075207:AAHy75gQAHyTFxIs0lg5Eu7MhiDckV6_2ak"

# المسار المؤقت لحفظ الفيديوهات
DOWNLOAD_PATH = "downloads"

# إنشاء مجلد التنزيل إذا لم يكن موجودًا
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# دالة لتحميل الفيديو
def download_video(url: str) -> str:
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
        'format': 'best',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename

# دالة بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل رابط الفيديو من YouTube أو أي منصة مدعومة.")

# دالة استقبال الرابط وتنزيله
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    await update.message.reply_text("جاري تنزيل الفيديو، يرجى الانتظار...")
    try:
        file_path = download_video(url)
        await update.message.reply_video(video=open(file_path, 'rb'))
        os.remove(file_path)
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ أثناء التنزيل: {e}")

# تشغيل البوت
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()
