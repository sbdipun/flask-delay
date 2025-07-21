import re
import os
from os import environ, getenv

API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = int(os.getenv("CHAT_ID", ""))
