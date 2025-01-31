import discord
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))  # For channel storage method

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Regex pattern to detect URLs
URL_PATTERN = r'https?://\S+'

def save_to_file(link):
    """Save links to a text file"""
    with open('links.txt', 'a') as f:
        f.write(f"{link}\n")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Find all URLs in the message
    urls = re.findall(URL_PATTERN, message.content)
    
    if urls:
        for url in urls:
            # Method 1: Save to text file
            save_to_file(url)
            
            # Method 2: Send to specific channel
            channel = client.get_channel(CHANNEL_ID)
            if channel:
                await channel.send(f"Link saved from {message.author.mention}: {url}")
            else:
                print(f"Channel with ID {CHANNEL_ID} not found!")

client.run(TOKEN)