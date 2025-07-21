# main.py
from flask import Flask
import threading
from bot import run_bot
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram bot is running!", 200

# Run the bot in a background thread
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run()
