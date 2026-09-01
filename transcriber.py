import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Inisialisasi Gemini dengan SDK baru
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

TRANSCRIBE_PROMPT = """Tolong dengarkan audio/video berikut ini dengan teliti. 
Tuliskan semua transkrip percakapan atau teks yang diucapkan dari awal sampai akhir. 

PENTING UNTUK FORMATTING:
1. Jangan tulis dalam satu paragraf panjang! Pecah menjadi beberapa paragraf yang pendek dan rapi (setiap 2-3 kalimat ganti baris).
2. Gunakan tanda baca yang baik (koma, titik) agar enak dibaca.
3. Berikan emoji yang sesuai dengan konteks kalimat jika memungkinkan.
4. Jika ada bagian yang tidak jelas, beri tanda [tidak terdengar].
5. Buat dalam bahasa Indonesia yang natural."""

# Daftar model dari yang terbaru ke yang lebih lama
FALLBACK_MODELS = [
    'gemini-2.5-pro',
    'gemini-pro-latest',
    'gemini-3.7-flash',
    'gemini-3.6-flash'
]

def _process_file(file_path: str) -> str:
    try:
        print(f"[Transcriber] Mengupload file: {file_path}")
        # Upload file ke Gemini
        myfile = client.files.upload(file=file_path)
        
        print("[Transcriber] File berhasil diupload, mencari model yang tersedia...")
        
        # Loop semua model sebagai sistem otomatis
        for model_name in FALLBACK_MODELS:
            try:
                print(f"[Transcriber] Mencoba model: {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[myfile, TRANSCRIBE_PROMPT]
                )
                print(f"[Transcriber] Sukses menggunakan model: {model_name}")
                return response.text
            except Exception as e:
                error_msg = str(e)
                print(f"[Transcriber] Model {model_name} gagal: {error_msg}")
                # Jika error 503 (Unavailable) atau 429 (Quota Exceeded), lanjut ke model berikutnya
                if "503" in error_msg or "429" in error_msg or "UNAVAILABLE" in error_msg or "overloaded" in error_msg:
                    continue
                elif "404" in error_msg:
                    continue # Model tidak ditemukan, coba yang lain
                else:
                    # Kalau error aneh lainnya, berhenti
                    return f"Terjadi kesalahan saat memproses file dengan model {model_name}: {e}"
        
        return "Semua model server Google saat ini sedang penuh (Overload). Mohon tunggu beberapa menit lalu coba lagi."

    except Exception as e:
        print(f"[Transcriber Error] {e}")
        return f"Terjadi kesalahan saat memproses file: {e}"

def transcribe_audio_file(file_path: str) -> str:
    return _process_file(file_path)

def transcribe_video_file(file_path: str) -> str:
    return _process_file(file_path)

