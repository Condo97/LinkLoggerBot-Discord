import os
from dotenv import load_dotenv

load_dotenv()

# Database
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_SCHEMA')
}

# OpenAI/DeepSeek
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
DEEPSEEK_MODEL = "deepseek/deepseek-r1:free"

# Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ALLOWED_CHANNELS = ['links', 'bot-commands']