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
    "facebook.com", "fb.watch",
    "vt.tiktok.com"
]

def is_valid_url(text: str) -> bool:
    url_pattern = re.compile(r'https?://[^\s]+')
    return bool(url_pattern.match(text.strip()))

def is_supported_url(url: str) -> bool:
    return any(domain in url for domain in SUPPORTED_DOMAINS)

def _download_via_tikwm(url: str, output_dir: str) -> Optional[str]:
    try:
        print("[Downloader] Mencoba TikWM API...")
        res = requests.get(
            "https://www.tikwm.com/api/",
            params={"url": url, "hd": 1},
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        data = res.json()
        if data.get("code") == 0:
            video_url = data["data"].get("play") or data["data"].get("music")
            if not video_url:
                return None
            video_res = requests.get(video_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            video_path = os.path.join(output_dir, "tiktok_video.mp4")
            with open(video_path, 'wb') as f:
                f.write(video_res.content)
            print("[Downloader] TikWM API berhasil!")
            return video_path
        else:
            print(f"[Downloader] TikWM API gagal: {data}")
            return None
    except Exception as e:
        print(f"[Downloader] TikWM API error: {e}")
        return None

def _download_via_ytdlp(url: str, output_dir: str) -> Optional[str]:
    try:
        print("[Downloader] Mencoba yt-dlp untuk TikTok...")
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(output_dir, 'tiktok_video.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'max_filesize': 50 * 1024 * 1024,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
                'Referer': 'https://www.tiktok.com/',
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # Cari file yang didownload
        for f in os.listdir(output_dir):
            if f.startswith("tiktok_video"):
                print("[Downloader] yt-dlp berhasil!")
                return os.path.join(output_dir, f)
        return None
    except Exception as e:
        print(f"[Downloader] yt-dlp error: {e}")
        return None

def download_tiktok_audio(url: str, output_dir: str) -> Optional[str]:
    # Coba TikWM dulu, lalu fallback ke yt-dlp
    result = _download_via_tikwm(url, output_dir)
    if result:
        return result
    print("[Downloader] TikWM gagal, mencoba yt-dlp sebagai fallback...")
    return _download_via_ytdlp(url, output_dir)

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
            for f in os.listdir(output_dir):
                if f.startswith(video_id):
                    return os.path.join(output_dir, f)
    except Exception as e:
        print(f"[Downloader Error] {e}")
        return None

    return None
