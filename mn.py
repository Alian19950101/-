import os
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio

BOT_TOKEN = "7872075207:AAHy75gQAHyTFxIs0lg5Eu7MhiDckV6_2ak"
DOWNLOAD_PATH = "downloads"
PORT = int(os.environ.get("PORT", 10000))  # Render يستخدم هذا البورت

os.makedirs(DOWNLOAD_PATH, exist_ok=True)

def download_video(url: str) -> str:
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title).40s.%(ext)s'),
        'format': 'best',
        'quiet': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أرسل رابط من أي منصة وسأقوم بتحميل الفيديو لك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⏳ جاري تحميل الفيديو...")
    try:
        file_path = download_video(url)
        await update.message.reply_video(video=open(file_path, 'rb'))
        os.remove(file_path)
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {e}")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # تفعيل Webhook بدلًا من Polling
    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    asyncio.run(main())
