# discord_bot.py
import discord
import re
from discord.ext import commands
from typing import List
from config import DISCORD_TOKEN, LINKS_CHANNEL, COMMAND_CHANNEL, DB_CONFIG
from linkbot.database import DBClient
from linkbot.openai_client import OpenAIClient
from linkbot.web_scraper import WebScraper
from linkbot.models import Link
from linkbot.backtick_scrubber import BacktickScrubber

class LinkBot(commands.Bot):
    def __init__(self, db_client: DBClient, ai_client: OpenAIClient):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.db = db_client
        self.ai = ai_client
        self.scraper = WebScraper()

    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.channel.name == COMMAND_CHANNEL:
            await self.process_command(message)
        else:
            await self.process_shared_links(message)

    async def process_shared_links(self, message):
        urls = re.findall(r'https?://\S+', message.content)
        if not urls:
            return

        links_channel = discord.utils.get(message.guild.channels, name=LINKS_CHANNEL)
        if not links_channel:
            return

        async with links_channel.typing():
            for url in urls:
                try:
                    content = await self.scraper.get_web_content(url)
                    summary = await self.ai.generate_summary(content) if content else "No summary available"
                    
                    link_id = self.db.save_link(url, summary)
                    
                    if link_id != -1:
                        # Format the URL as a markdown link to suppress preview
                        formatted_url = f"[{url}]({url})"  # Hide preview while keeping it clickable
                        await links_channel.send(
                            f"New link saved {formatted_url} from {message.author.mention}"
                        )
                except Exception as e:
                    print(f"Error processing link: {str(e)}")
                    # Send link to links channel if there was an error processing
                    formatted_url = f"[{url}]({url})"  # Hide preview while keeping it clickable
                    await links_channel.send(
                        f"New link saved {formatted_url} from {message.author.mention}"
                    )

    async def process_command(self, message):
        try:
            async with message.channel.typing():  # Show typing in command channel
                classification = await self.ai.classify_command(message.content)
                
                if not isinstance(classification, dict):
                    classification = {"command_type": "NONE"}
                    
                command_type = classification.get("command_type", "NONE")
                timeframe_days = classification.get("timeframe_days")
                max_results = classification.get("max_results")

                if command_type == "NONE":
                    response = await self.ai.generate_response(message.content, [])
                else:
                    links = self.db.get_recent_links(
                        days_ago=timeframe_days,
                        limit=max_results
                    )

                    if not links:
                        response = "No relevant links found in my records."
                    else:
                        try:
                            context = await self._build_command_context(command_type, links, message.content)
                            response = await self.ai.generate_response(message.content, context)
                        except Exception as e:
                            print(f"Context building failed: {str(e)}")
                            response = "Error processing your request."

                await message.channel.send(response[:2000])

        except Exception as e:
            print(f"Command processing error: {str(e)}")
            await message.channel.send("⚠️ An error occurred while processing your request.")

    def _get_links_for_command(self, classification: dict) -> list[Link]:
        days = classification.get('timeframe_days')
        limit = classification.get('max_results')
        return self.db.get_recent_links(days_ago=days, limit=limit)

    async def _build_command_context(self, command_type: str, links: list[Link], query: str) -> list[str]:
        # link_ids = [str(link.link_id) for link in links]
        formatted_links = []
        for link in links:
            string = ""
            if link.link_id:
                string += f"ID: {link.link_id} | "
            if link.web_url:
                string += f"URL: {link.web_url} | "
            if link.summary:
                string += f"Summary: {link.summary[:200]}"
            formatted_links.append(string)

        if command_type == 'SEARCH':
            return formatted_links

        relevant_ids = await self.ai.filter_relevant_links(query, formatted_links)
        relevant_links = [link for link in links if str(link.link_id) in relevant_ids]
        
        if command_type == 'SEARCH_AND_SCRAPE':
            return await self._add_scraped_content(relevant_links)
        
        return formatted_links

    async def _add_scraped_content(self, links: list[Link]) -> list[str]:
        context = []
        for link in links:
            content = await self.scraper.get_web_content(link.web_url)
            context.append(
                f"ID: {link.link_id} | URL: {link.web_url}\n"
                f"Fresh Content: {content[:1000] if content else 'Unable to retrieve content'}"
            )
        return context
    
    import re

def main():
    db = DBClient(DB_CONFIG)
    ai = OpenAIClient()
    bot = LinkBot(db, ai)
    bot.run(DISCORD_TOKEN)