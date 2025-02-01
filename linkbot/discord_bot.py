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
        if message.author == self.user:
            return
            
        try:
            # Get context and classify
            context = await self._get_context(message.content)
            classification = await self.chat_client.classify(message.content, context)
            
            # Safely access classification values
            needs_scraping = classification.get('needs_scraping', []) or []
            if needs_scraping:
                await self._handle_scraping(needs_scraping)
                
            # Get updated context
            updated_context = await self._get_context_with_classification(classification)
            
            # Generate and send response
            response = await self.chat_client.completion(
                message.content,
                updated_context
            )
            await message.channel.send(response[:2000])
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            await message.channel.send("⚠️ An error occurred while processing your request")
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            await message.channel.send("Sorry, I encountered an error processing your request.")

    async def _get_context_with_classification(self, classification: dict) -> list[str]:
        """Get context based on classification parameters"""
        days_ago = classification.get('link_query_days_ago_limit')
        count_limit = classification.get('link_query_count_limit')
        
        if days_ago:
            links = self.db.get_recent_links(days_ago=days_ago)
        elif count_limit:
            links = self.db.get_recent_links(limit=count_limit)
        else:
            links = self.db.get_recent_links(limit=5)
            
        return [
            f"Link {link.link_id}: {link.web_url}\nSummary: {link.summary}"
            for link in links
        ]

    async def _handle_scraping(self, link_ids: list[int]):
        """Handle scraping of specified links"""
        for link_id in link_ids:
            link = self.db.get_link_by_id(link_id)
            if link:
                print(f"Scraping {link.web_url}")
                content = await self.scraper.get_web_content(link.web_url)
                if content:
                    self.db.update_link_summary(link_id, content[:1000])
    
    async def _get_context(self, message: str) -> list[str]:
        """Get base context with recent links"""
        # Get 5 most recent links by default
        recent_links = self.db.get_recent_links(limit=5)
        
        # Format context entries
        context_entries = [
            f"Link ID: {link.link_id}\nURL: {link.web_url}\nSummary: {link.summary}\n"
            for link in recent_links
        ]
        
        # Add system message as first context entry
        return [
            "Current link context (most recent first):",
            *context_entries
        ]

    async def _get_context_with_classification(self, classification: dict) -> list[str]:
        """Get filtered context based on classification"""
        # Get links based on classification parameters
        if classification.get('link_query_days_ago_limit'):
            links = self.db.get_recent_links(
                days_ago=classification['link_query_days_ago_limit']
            )
        elif classification.get('link_query_count_limit'):
            links = self.db.get_recent_links(
                limit=classification['link_query_count_limit']
            )
        else:
            links = self.db.get_recent_links(limit=3)  # Default to 3 links
        
        # Format context entries with scraped data
        return [
            f"Link ID: {link.link_id}\nURL: {link.web_url}\nSummary: {link.summary}\n"
            for link in links
        ]

def main():
    db_client = DBClient(DB_CONFIG)
    chat_client = ChatClient()
    bot = LinkBot(db_client, chat_client)
    bot.run(DISCORD_TOKEN)