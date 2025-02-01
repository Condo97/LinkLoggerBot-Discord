# config.py (unchanged)
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_SCHEMA')
}

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
DEEPSEEK_MODEL = "deepseek/deepseek-chat"
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
LINKS_CHANNEL = 'links'
COMMAND_CHANNEL = 'bot-commands'