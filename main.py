from flask import Flask
import threading
from bot import run_bot
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running via Flask!"

# Start the bot in a background thread
threading.Thread(target=run_bot).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
