import discord
from discord.ext import commands
from config import DISCORD_TOKEN, ALLOWED_CHANNELS, DB_CONFIG
from linkbot.database import DBClient
from linkbot.openai_client import ChatClient
from linkbot.web_scraper import WebScraper

class LinkBot(commands.Bot):
    def __init__(self, db_client, chat_client):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.db = db_client
        self.chat_client = chat_client
        self.scraper = WebScraper()
        
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        
    async def on_message(self, message):
        if message.channel.name not in ALLOWED_CHANNELS:
            return
        
        # Process message
        context = await self._get_context(message.content)
        classification = await self.chat_client.classify(message.content, context)
        
        # Process commands
        if classification['needs_scraping']:
            await self._handle_scraping(classification['needs_scraping'])
        
        # Generate response
        updated_context = await self._get_updated_context(classification)
        response = await self.chat_client.completion(message.content, updated_context)
        await message.channel.send(response)
    
    async def _get_context(self, message: str) -> list[str]:
        # Get recent links and summaries
        recent_links = self.db.get_recent_links(limit=5)
        return [
            f"Link {link.link_id}: {link.web_url}\nSummary: {link.summary}"
            for link in recent_links
        ]
    
    async def _handle_scraping(self, link_ids: list[int]):
        for link_id in link_ids:
            link = self.db.get_link_by_id(link_id)
            if link:
                content = await self.scraper.get_web_content(link.web_url)
                self.db.update_link_summary(link_id, content[:1000])  # Store first 1000 chars

def main():
    db_client = DBClient(DB_CONFIG)
    chat_client = ChatClient()
    bot = LinkBot(db_client, chat_client)
    bot.run(DISCORD_TOKEN)