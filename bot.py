# bot.py
from pyrogram import Client, filters
from pyrogram.types import Message
import os
import subprocess
import numpy as np
import soundfile as sf
import requests
import time
import logging
from config import *


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

def download_partial_audio(url, output_path, duration=60):
    cmd = [
        'ffmpeg', '-y', '-ss', '0', '-t', str(duration),
        '-i', url,
        '-vn', '-ac', '1', '-ar', '16000',
        '-f', 'wav', output_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

def download_partial_video(url, output_path, duration=60):
    cmd = [
        'ffmpeg', '-y', '-ss', '0', '-t', str(duration),
        '-i', url,
        '-an', '-c:v', 'libx264', '-preset', 'ultrafast', output_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

def extract_audio_stream(url, output_path, duration=60):
    cmd = [
        'ffmpeg', '-y', '-ss', '0', '-t', str(duration),
        '-i', url,
        '-vn', '-c:a', 'copy', output_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

def read_audio(file_path):
    y, sr = sf.read(file_path)
    if y.ndim > 1:
        y = y[:, 0]
    return y, sr

def fft_cross_correlation(ref_signal, target_signal, sr):
    n = len(ref_signal) + len(target_signal) - 1
    X = np.fft.fft(ref_signal, n=n)
    Y = np.fft.fft(target_signal, n=n)
    corr = np.fft.ifft(X * np.conj(Y)).real
    delay_index = np.argmax(corr)
    if delay_index > n // 2:
        delay_index -= n
    delay_sec = delay_index / sr
    return delay_sec * 1000  # ms

def send_to_telegram(file_path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    with open(file_path, 'rb') as f:
        response = requests.post(url, data={'chat_id': CHAT_ID, 'caption': caption}, files={'video': f})
    return response.ok

@bot.on_message(filters.command("delay") & (filters.private | filters.group))
async def delay_handler(client: Client, message: Message):
    try:
        args = message.text.split()
        if len(args) != 3:
            await message.reply("Usage: /delay <Hindi_Audio_URL> <English_Video_URL>")
            return

        hindi_url, english_url = args[1], args[2]
        await message.reply("⏬ Downloading and processing...")

        start_time = time.time()
        download_partial_audio(hindi_url, "hindi.wav")
        download_partial_audio(english_url, "english.wav")

        hindi, sr1 = read_audio("hindi.wav")
        english, sr2 = read_audio("english.wav")
        if sr1 != sr2:
            raise ValueError("Sample rates don't match!")

        delay_ms = fft_cross_correlation(english, hindi, sr1)

        if delay_ms > 0:
            note = f"🔁 Hindi audio lags English by {delay_ms:.2f} ms"
            delay_str = f"{delay_ms/1000:.3f}"
        elif delay_ms < 0:
            note = f"🔁 Hindi audio leads English by {abs(delay_ms):.2f} ms"
            delay_str = f"-{abs(delay_ms)/1000:.3f}"
        else:
            note = "✅ Hindi audio is perfectly aligned"
            delay_str = "0"

        download_partial_video(english_url, "video.mp4")
        extract_audio_stream(english_url, "eng.m4a")
        extract_audio_stream(hindi_url, "hin.m4a")

        if float(delay_str) >= 0:
            subprocess.run([
                'ffmpeg', '-y',
                '-i', 'hin.m4a',
                '-af', f"adelay={int(float(delay_str)*1000)}|{int(float(delay_str)*1000)}",
                '-c:a', 'aac', '-b:a', '192k',
                'hindi_delayed.m4a'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        else:
            subprocess.run([
                'ffmpeg', '-y',
                '-ss', str(abs(float(delay_str))),
                '-i', 'hin.m4a',
                '-c:a', 'aac', '-b:a', '192k',
                'hindi_delayed.m4a'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        subprocess.run([
            'ffmpeg', '-y',
            '-i', 'video.mp4',
            '-i', 'eng.m4a',
            '-i', 'hindi_delayed.m4a',
            '-map', '0:v:0', '-map', '1:a:0', '-map', '2:a:0',
            '-c:v', 'copy', '-c:a', 'aac',
            '-shortest',
            '-metadata:s:a:0', 'language=eng',
            '-metadata:s:a:1', 'language=hin',
            'preview_fixed.mp4'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        send_to_telegram('preview_fixed.mp4', f"🧪 Preview File\n{note}")
        await message.reply(f"✅ Done! {note}")

    except Exception as e:
        logger.exception("Error in /delay command")
        await message.reply(f"❌ Error: {e}")

def run_bot():
    bot.run()
