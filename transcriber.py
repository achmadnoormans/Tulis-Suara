import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

FORMAT_PROMPT = """Tolong perbaiki format transkrip mentah berikut ini. 

PENTING UNTUK FORMATTING:
1. Jangan tulis dalam satu paragraf panjang! Pecah menjadi beberapa paragraf yang pendek dan rapi (setiap 2-3 kalimat ganti baris).
2. Gunakan tanda baca yang baik (koma, titik) agar enak dibaca.
3. Berikan emoji yang sesuai dengan konteks kalimat jika memungkinkan.
4. Buat dalam bahasa Indonesia yang natural.
5. HANYA KELUARKAN HASIL TRANSKRIPNYA SAJA (jangan tambahkan kata pengantar seperti 'Ini dia transkripnya').

Transkrip mentah:
{raw_text}
"""

# Daftar model LLM Groq sebagai cadangan otomatis jika ada yang dihapus/error
FALLBACK_LLM_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "groq/compound-mini",
    "allam-2-7b"
]

def _process_file(file_path: str) -> str:
    try:
        print(f"[Transcriber] Memulai transkripsi Groq untuk file: {file_path}")
        
        # Langkah 1: Transkripsi audio/video ke teks menggunakan Whisper
        with open(file_path, "rb") as file:
            print("[Transcriber] Mengirim file ke Groq Whisper API...")
            try:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(file_path), file.read()),
                    model="whisper-large-v3-turbo",
                    response_format="text",
                    language="id"
                )
            except Exception as e:
                # Jika model turbo gagal, coba model utamanya
                print(f"[Transcriber] whisper-large-v3-turbo gagal: {e}, mencoba whisper-large-v3...")
                file.seek(0)
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(file_path), file.read()),
                    model="whisper-large-v3",
                    response_format="text",
                    language="id"
                )
        
        raw_text = transcription
        if not raw_text or len(raw_text.strip()) == 0:
            return "Tidak ada suara percakapan yang terdeteksi di dalam video."
            
        print("[Transcriber] Transkripsi selesai. Memformat teks...")
        
        # Langkah 2: Merapikan format teks menggunakan LLM dengan Auto-Fallback
        for model_name in FALLBACK_LLM_MODELS:
            try:
                print(f"[Transcriber] Memformat menggunakan model {model_name}...")
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": FORMAT_PROMPT.format(raw_text=raw_text)
                        }
                    ],
                    model=model_name,
                )
                final_text = chat_completion.choices[0].message.content
                print(f"[Transcriber] Berhasil memformat menggunakan {model_name}!")
                return final_text
            except Exception as e:
                print(f"[Transcriber] Model {model_name} gagal: {e}")
                continue # Lanjut ke model berikutnya
        
        return "Gagal memformat teks: Semua model LLM Groq sedang tidak tersedia/error."
        
    except Exception as e:
        print(f"[Transcriber Error] {e}")
        return f"Terjadi kesalahan saat memproses file di Groq: {e}"

def transcribe_audio_file(file_path: str) -> str:
    return _process_file(file_path)

def transcribe_video_file(file_path: str) -> str:
    return _process_file(file_path)
