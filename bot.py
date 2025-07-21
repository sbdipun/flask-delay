# bot.py
from pyrogram import Client, filters
from pyrogram.types import Message
import os
import asyncio
import subprocess
import numpy as np
import soundfile as sf
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

# List of temporary files to delete after processing
TEMP_FILES = [
    "hindi.wav", "english.wav", "video.mp4",
    "eng.m4a", "hin.m4a", "hindi_delayed.m4a",
    "preview_fixed.mp4"
]

async def run_subprocess(cmd):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if stderr:
        logger.error(stderr.decode())
    return stdout, stderr

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

async def delay_handler(client: Client, message: Message):
    try:
        args = message.text.split()
        if len(args) != 3:
            await message.reply("Usage: /delay <Hindi_Audio_URL> <English_Video_URL>")
            return

        hindi_url, english_url = args[1], args[2]
        await message.reply("⏬ Downloading and processing...")

        # Step 1: Download partial audio files
        await asyncio.gather(
            run_subprocess([
                'ffmpeg', '-y', '-ss', '0', '-t', '60',
                '-i', hindi_url,
                '-vn', '-ac', '1', '-ar', '16000',
                '-f', 'wav', 'hindi.wav'
            ]),
            run_subprocess([
                'ffmpeg', '-y', '-ss', '0', '-t', '60',
                '-i', english_url,
                '-vn', '-ac', '1', '-ar', '16000',
                '-f', 'wav', 'english.wav'
            ])
        )

        # Read audio files
        hindi, sr1 = read_audio("hindi.wav")
        english, sr2 = read_audio("english.wav")
        if sr1 != sr2:
            raise ValueError("Sample rates don't match!")

        delay_ms = fft_cross_correlation(english, hindi, sr1)

        if delay_ms > 0:
            note = f"🔁 Hindi audio lags English by {delay_ms:.2f} ms"
            delay_str = f"{delay_ms / 1000:.3f}"
        elif delay_ms < 0:
            note = f"🔁 Hindi audio leads English by {abs(delay_ms):.2f} ms"
            delay_str = f"-{abs(delay_ms) / 1000:.3f}"
        else:
            note = "✅ Hindi audio is perfectly aligned"
            delay_str = "0"

        # Step 2: Download video and extract audio
        await asyncio.gather(
            run_subprocess([
                'ffmpeg', '-y', '-ss', '0', '-t', '60',
                '-i', english_url,
                '-an', '-c:v', 'libx264', '-preset', 'ultrafast', 'video.mp4'
            ]),
            run_subprocess([
                'ffmpeg', '-y', '-ss', '0', '-t', '60',
                '-i', english_url,
                '-vn', '-c:a', 'copy', 'eng.m4a'
            ]),
            run_subprocess([
                'ffmpeg', '-y', '-ss', '0', '-t', '60',
                '-i', hindi_url,
                '-vn', '-c:a', 'copy', 'hin.m4a'
            ])
        )

        # Step 3: Apply delay or trim
        if float(delay_str) >= 0:
            await run_subprocess([
                'ffmpeg', '-y',
                '-i', 'hin.m4a',
                '-af', f"adelay={int(float(delay_str) * 1000)}|{int(float(delay_str) * 1000)}",
                '-c:a', 'aac', '-b:a', '192k',
                'hindi_delayed.m4a'
            ])
        else:
            await run_subprocess([
                'ffmpeg', '-y',
                '-ss', str(abs(float(delay_str))),
                '-i', 'hin.m4a',
                '-c:a', 'aac', '-b:a', '192k',
                'hindi_delayed.m4a'
            ])

        # Step 4: Combine video and audio
        await run_subprocess([
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
        ])

        # Step 5: Send result via Pyrogram
        await client.send_video(
            chat_id=message.chat.id,
            video='preview_fixed.mp4',
            caption=f"🧪 Preview File\n{note}"
        )

        await message.reply(f"✅ Done! {note}")

    except Exception as e:
        logger.exception("Error in /delay command")
        await message.reply(f"❌ Error: {e}")
    finally:
        # Step 6: Cleanup temp files
        for file in TEMP_FILES:
            if os.path.exists(file):
                os.remove(file)
                logger.info(f"Removed temp file: {file}")

# Register handler
bot.on_message(filters.command("delay") & (filters.private | filters.group))(delay_handler)

def run_bot():
    bot.run()

if __name__ == "__main__":
    run_bot()
