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

def _process_file(file_path: str) -> str:
    try:
        print(f"[Transcriber] Memulai transkripsi Groq untuk file: {file_path}")
        
        # Langkah 1: Transkripsi audio/video ke teks menggunakan Whisper
        with open(file_path, "rb") as file:
            print("[Transcriber] Mengirim file ke Groq Whisper API...")
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(file_path), file.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
                language="id"
            )
        
        raw_text = transcription
        if not raw_text or len(raw_text.strip()) == 0:
            return "Tidak ada suara percakapan yang terdeteksi di dalam video."
            
        print("[Transcriber] Transkripsi selesai. Memformat teks...")
        
        # Langkah 2: Merapikan format teks menggunakan LLaMA 3
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": FORMAT_PROMPT.format(raw_text=raw_text)
                }
            ],
            model="llama-3.1-8b-instant",
        )
        
        final_text = chat_completion.choices[0].message.content
        print("[Transcriber] Proses selesai!")
        return final_text
        
    except Exception as e:
        print(f"[Transcriber Error] {e}")
        return f"Terjadi kesalahan saat memproses file di Groq: {e}"

def transcribe_audio_file(file_path: str) -> str:
    return _process_file(file_path)

def transcribe_video_file(file_path: str) -> str:
    return _process_file(file_path)
