# main.py
from flask import Flask
import threading
import asyncio
from bot import run_bot

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!", 200

def start_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())  # <-- Fix!
    run_bot()  # This calls bot.run()

# Start the bot in a background thread
threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    app.run()
