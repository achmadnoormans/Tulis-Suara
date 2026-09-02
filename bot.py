import os
import tempfile
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from downloader import is_valid_url, is_supported_url, download_audio_from_url
from transcriber import transcribe_audio_file, transcribe_video_file

# Load .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /start"""
    await update.message.reply_text(
        "👋 Halo! Aku bot transkripsi video.\n\n"
        "📌 *Cara pakai:*\n"
        "1️⃣ Kirim *link video* (YouTube, TikTok, Instagram, dll)\n"
        "2️⃣ *Upload file video/audio* langsung ke chat\n\n"
        "⏳ Aku akan mengubah isi video menjadi teks untuk kamu!\n\n"
        "Ketik /help untuk bantuan lebih lanjut.",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /help"""
    await update.message.reply_text(
        "📖 *Panduan Penggunaan:*\n\n"
        "🔗 *Dari Link:*\n"
        "Langsung paste link YouTube, TikTok, Instagram, Twitter/X, atau Facebook.\n\n"
        "📁 *Dari File:*\n"
        "Upload file video (MP4, MOV, dll) atau audio (MP3, M4A, dll) langsung ke chat.\n\n"
        "⚠️ *Batasan:*\n"
        "• Ukuran file maks: 50MB\n"
        "• Video terlalu panjang (>1 jam) mungkin kurang akurat\n"
        "• Video privat/terkunci tidak bisa diproses\n\n"
        "💬 Ada pertanyaan? Hubungi admin.",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
# MESSAGE HANDLERS
# ─────────────────────────────────────────────

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler saat user kirim link teks."""
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text("⚠️ Format URL tidak valid. Coba lagi dengan link yang benar.")
        return

    if not is_supported_url(url):
        await update.message.reply_text(
            "⚠️ Platform ini belum didukung.\n"
            "Platform yang didukung: YouTube, TikTok, Instagram, Twitter/X, Facebook."
        )
        return

    status_msg = await update.message.reply_text("⏳ Sedang mengunduh video... Mohon tunggu.")

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Download audio
            await status_msg.edit_text("⬇️ Mengunduh audio dari link...")
            audio_path = download_audio_from_url(url, tmpdir)

            if not audio_path:
                await status_msg.edit_text(
                    "❌ Gagal mengunduh video. Kemungkinan:\n"
                    "• Video privat atau terkunci\n"
                    "• Link sudah expired\n"
                    "• Platform tidak didukung"
                )
                return

            # Transkripsi
            await status_msg.edit_text("🤖 AI sedang memproses transkripsi...")
            transcript = transcribe_audio_file(audio_path)

            # Kirim hasil
            await status_msg.delete()
            await send_transcript(update, transcript, source=url)

        except Exception as e:
            logger.error(f"Error handle_link: {e}")
            try:
                await status_msg.edit_text(f"❌ Terjadi kesalahan: {str(e)[:200]}")
            except:
                await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)[:200]}")


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler saat user upload file video."""
    status_msg = await update.message.reply_text("⏳ Menerima video... Mohon tunggu.")

    video = update.message.video or update.message.document
    if not video:
        await status_msg.edit_text("❌ Tidak ada file video yang terdeteksi.")
        return

    # Cek ukuran file (50MB limit)
    if video.file_size and video.file_size > 50 * 1024 * 1024:
        await status_msg.edit_text("❌ File terlalu besar. Maksimal 50MB.")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Download file dari Telegram
            await status_msg.edit_text("⬇️ Mengunduh file video...")
            file = await context.bot.get_file(video.file_id)
            video_path = os.path.join(tmpdir, "video.mp4")
            await file.download_to_drive(video_path)

            # Transkripsi
            await status_msg.edit_text("🤖 AI sedang memproses transkripsi...")
            import asyncio
            transcript = await asyncio.to_thread(transcribe_video_file, video_path)

            # Kirim hasil
            await status_msg.delete()
            await send_transcript(update, transcript, source="File upload")

        except Exception as e:
            logger.error(f"Error handle_video: {e}")
            try:
                await status_msg.edit_text(f"❌ Terjadi kesalahan: {str(e)[:200]}")
            except:
                await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)[:200]}")


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler saat user upload file audio."""
    status_msg = await update.message.reply_text("⏳ Menerima audio... Mohon tunggu.")

    audio = update.message.audio or update.message.voice

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            await status_msg.edit_text("⬇️ Mengunduh file audio...")
            file = await context.bot.get_file(audio.file_id)
            audio_path = os.path.join(tmpdir, "audio.mp3")
            await file.download_to_drive(audio_path)

            await status_msg.edit_text("🤖 AI sedang memproses transkripsi...")
            transcript = transcribe_audio_file(audio_path)

            await status_msg.delete()
            await send_transcript(update, transcript, source="Audio upload")

        except Exception as e:
            logger.error(f"Error handle_audio: {e}")
            await status_msg.edit_text(f"❌ Terjadi kesalahan: {str(e)[:200]}")


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────

async def send_transcript(update: Update, transcript: str, source: str = ""):
    """Kirim hasil transkripsi ke user, potong jika terlalu panjang."""
    header = f"📄 *Hasil Transkripsi*\n"
    if source:
        header += f"🔗 Sumber: `{source[:100]}`\n"
    header += "\n"

    full_text = header + transcript

    # Telegram max 4096 karakter per pesan
    MAX_LEN = 4096
    try:
        if len(full_text) <= MAX_LEN:
            await update.message.reply_text(full_text, parse_mode="Markdown")
        else:
            await update.message.reply_text(header + "_(Teks panjang, dikirim dalam beberapa bagian)_", parse_mode="Markdown")
            chunks = [transcript[i:i+4000] for i in range(0, len(transcript), 4000)]
            for i, chunk in enumerate(chunks, 1):
                await update.message.reply_text(
                    f"📄 *Bagian {i}/{len(chunks)}:*\n\n{chunk}",
                    parse_mode="Markdown"
                )
    except Exception:
        # Fallback without markdown formatting if it fails due to unescaped characters
        if len(full_text) <= MAX_LEN:
            await update.message.reply_text(full_text)
        else:
            await update.message.reply_text(header + "(Teks panjang, dikirim dalam beberapa bagian)")
            chunks = [transcript[i:i+4000] for i in range(0, len(transcript), 4000)]
            for i, chunk in enumerate(chunks, 1):
                await update.message.reply_text(f"Bagian {i}/{len(chunks)}:\n\n{chunk}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────


import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

def main():
    """Jalankan bot."""
    print("🤖 Bot transkripsi sedang berjalan...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Video & audio upload
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.Document.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))

    # Link teks
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    # Mulai polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
