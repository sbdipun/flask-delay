# main.py
from flask import Flask
import threading
from bot import run_bot  # Import the bot runner

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Start the bot in a background thread
threading.Thread(target=run_bot).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
