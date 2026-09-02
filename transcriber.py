import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

FORMAT_PROMPT = """Tolong perbaiki format transkrip berikut ini agar sangat rapi dan enak dibaca. 

ATURAN FORMATTING (SANGAT PENTING):
1. GABUNGKAN beberapa kalimat menjadi SATU PARAGRAF utuh (idealnya 2-3 kalimat per paragraf). Jangan buat baris baru untuk setiap kalimat pendek!
2. Di awal setiap paragraf, tuliskan rentang waktu (timestamp) gabungannya dengan format **TEBAL**, contoh: **[00:00 - 00:15]** Teks paragraf disini...
3. WAJIB BERIKAN JARAK 1 BARIS KOSONG (ENTER) ANTAR PARAGRAF agar tidak terlihat menumpuk dan mudah dibaca.
4. Gunakan tanda baca yang baik (koma, titik, huruf kapital).
5. Berikan emoji yang relevan di akhir atau di dalam kalimat.
6. HANYA KELUARKAN HASIL TRANSKRIPNYA SAJA (jangan tambahkan kata pengantar apapun).

Transkrip mentah (dengan timestamp tiap kalimat):
{raw_text}
"""

FALLBACK_LLM_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "groq/compound-mini",
    "allam-2-7b"
]

def format_seconds(seconds: float) -> str:
    """Mengubah detik (float) menjadi format MM:SS"""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def _process_file(file_path: str) -> str:
    try:
        print(f"[Transcriber] Memulai transkripsi Groq untuk file: {file_path}")
        
        # Langkah 1: Transkripsi audio/video ke teks dengan Timestamp (verbose_json)
        with open(file_path, "rb") as file:
            print("[Transcriber] Mengirim file ke Groq Whisper API (verbose_json)...")
            try:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(file_path), file.read()),
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json",
                    language="id"
                )
            except Exception as e:
                print(f"[Transcriber] whisper-large-v3-turbo gagal: {e}, mencoba whisper-large-v3...")
                file.seek(0)
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(file_path), file.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    language="id"
                )
        
        segments = getattr(transcription, "segments", [])
        if not segments:
            # Jika fallback string / tidak ada segmen
            if isinstance(transcription, str) and len(transcription.strip()) > 0:
                raw_text = transcription
            else:
                return "Tidak ada suara percakapan yang terdeteksi di dalam video."
        else:
            # Bangun teks dengan timestamp
            raw_text = ""
            for seg in segments:
                start_time = format_seconds(seg.get('start', 0))
                end_time = format_seconds(seg.get('end', 0))
                text = seg.get('text', '').strip()
                raw_text += f"[{start_time} - {end_time}] {text}\n"
            
        print("[Transcriber] Transkripsi selesai. Memformat teks beserta waktunya...")
        
        # Langkah 2: Merapikan format teks menggunakan LLM
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
                continue
        
        return "Gagal memformat teks: Semua model LLM Groq sedang tidak tersedia/error."
        
    except Exception as e:
        print(f"[Transcriber Error] {e}")
        return f"Terjadi kesalahan saat memproses file di Groq: {e}"

def transcribe_audio_file(file_path: str) -> str:
    return _process_file(file_path)

def transcribe_video_file(file_path: str) -> str:
    return _process_file(file_path)
