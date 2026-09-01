import os
import re
import yt_dlp
import requests
import tempfile
from typing import Optional

SUPPORTED_DOMAINS = [
    "youtube.com", "youtu.be",
    "instagram.com", "tiktok.com",
    "twitter.com", "x.com",
    "facebook.com", "fb.watch"
]

def is_valid_url(text: str) -> bool:
    url_pattern = re.compile(r'https?://[^\s]+')
    return bool(url_pattern.match(text.strip()))

def is_supported_url(url: str) -> bool:
    return any(domain in url for domain in SUPPORTED_DOMAINS)

def download_tiktok_audio(url: str, output_dir: str) -> Optional[str]:
    try:
        print("[Downloader] Menggunakan TikWM API untuk TikTok")
        res = requests.get("https://www.tikwm.com/api/", params={"url": url, "hd": 1})
        data = res.json()
        if data.get("code") == 0:
            video_url = data["data"].get("play") or data["data"].get("music")
            if not video_url:
                return None
            
            # Download file from URL
            video_res = requests.get(video_url)
            video_path = os.path.join(output_dir, "tiktok_video.mp4")
            with open(video_path, 'wb') as f:
                f.write(video_res.content)
            return video_path
        else:
            print("[Downloader Error] TikWM API Gagal:", data)
            return None
    except Exception as e:
        print(f"[Downloader Error] TikTok extraction failed: {e}")
        return None

def download_audio_from_url(url: str, output_dir: str) -> Optional[str]:
    if "tiktok.com" in url:
        return download_tiktok_audio(url, output_dir)
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'max_filesize': 50 * 1024 * 1024,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id', 'audio')
            audio_path = os.path.join(output_dir, f"{video_id}.mp3")
            if os.path.exists(audio_path):
                return video_path
            for f in os.listdir(output_dir):
                if f.startswith(video_id):
                    return os.path.join(output_dir, f)
    except Exception as e:
        print(f"[Downloader Error] {e}")
        return None

    return None
