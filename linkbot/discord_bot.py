# discord_bot.py
import asyncio
import discord
import re
from discord.ext import commands
from typing import List, Optional
from linkbot.config import DISCORD_TOKEN, LINKS_CHANNEL, COMMAND_CHANNEL, PRODUCTS_CHANNEL, DB_CONFIG, CONTEXT_MESSAGE_COUNT
from linkbot.channel_exclusion import ChannelExclusionService
from linkbot.database import DBClient
from linkbot.openai_client import OpenAIClient
from linkbot.web_scraper import WebScraper
from linkbot.models import Link
from linkbot.backtick_scrubber import BacktickScrubber
from linkbot.link_categorizer import LinkCategorizer

class LinkBot(commands.Bot):
    def __init__(self, db_client: DBClient, ai_client: OpenAIClient):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)
        self.db = db_client
        self.ai = ai_client
        self.scraper = WebScraper()
        self.exclusion_service = ChannelExclusionService(db_client)
        self.categorizer = LinkCategorizer()
    
    ### Discord SDK
    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.channel.name == COMMAND_CHANNEL:
            await self.process_command(message)
        else:
            await self.process_shared_links(message)
    
    async def on_raw_reaction_add(self, payload):
        """Handle reaction add events""" # TODO: Try to rework this and potentially _extract_link_id_from_message
        try:
            # Only process in links channel
            channel = self.get_channel(payload.channel_id)
            if channel.name != LINKS_CHANNEL:
                return

            # Only process red X emoji
            if str(payload.emoji) != '❌':
                return

            # Get the message and user
            try:
                message = await channel.fetch_message(payload.message_id)
                user = await self.fetch_user(payload.user_id)
            except discord.NotFound:
                return

            # Permission check - only allow users with Manage Messages permission
            member = channel.guild.get_member(payload.user_id)
            if not member or not member.guild_permissions.manage_messages:
                return

            # Extract URL from message
            url = self._extract_url_from_message(message)
            if not url:
                return
            print(url)
            # Find matching link in database
            link = self.db.get_link_by_url(url)
            if not link:
                await channel.send(f"{user.mention} Could not find matching link in database!", delete_after=5)
                return

            # Delete from database
            success = self.db.delete_link(link.link_id)
            if not success:
                await channel.send(f"{user.mention} Failed to delete link from database!", delete_after=5)
                return

            # Delete the message
            try:
                await message.delete()
                await channel.send(f"{user.mention} Link successfully deleted!", delete_after=5)
            except discord.Forbidden:
                await channel.send(f"{user.mention} I don't have permission to delete messages!", delete_after=5)
            except discord.HTTPException as e:
                await channel.send(f"{user.mention} Failed to delete message: {str(e)}", delete_after=5)
        except Exception as e:
            print(f"Error processing reaction: {str(e)}")
            channel = self.get_channel(payload.channel_id)
            if channel:
                await channel.send("An error occurred while processing that reaction.", delete_after=5)

    ### Logic

    async def get_channel_context(self, channel, limit: int) -> List[str]:
        """Retrieve channel message history for AI context"""
        messages = []
        async for message in channel.history(limit=limit):
            messages.append(f"{message.author.display_name}: {message.content}")
        return messages[::-1]  # Return in chronological order

    async def process_shared_links(self, message):
        # Check if channel is excluded
        if str(message.channel.id) in self.exclusion_service.get_excluded_channels():
            return
        
        urls = re.findall(r'https?://\S+', message.content)
        if not urls:
            return

        links_channel = discord.utils.get(message.guild.channels, name=LINKS_CHANNEL)

        if not links_channel:
            return
        
        # Send loading messages
        loading_messages = []
        for url in urls:
            print(url)
            loading_messages.append(await links_channel.send(f"Loading data for <{url}>..."))
        
        async with links_channel.typing():
            for url in urls:
                try:
                    content = await self.scraper.get_web_content(url)
                    summary, category = await self.ai.generate_summary(content) if content else ("No summary available", "other")
                    
                    # Save/update link
                    link_id = self.db.save_link(url, summary, category)
                    
                    if link_id != -1:
                        # Check if this was an update
                        existing_link = self.db.get_link_by_url(url)
                        if existing_link and not existing_link.deleted:
                            message_text = f"Duplicate link updated <{url}> from {message.author.mention}"
                        else:
                            message_text = f"New link saved <{url}> from {message.author.mention}"
                            
                        await links_channel.send(message_text)

                        # If it is a product or service send in proudcts channel
                        products_channel = discord.utils.get(message.guild.channels, name=PRODUCTS_CHANNEL)
                        if products_channel:
                            products_channel.send(f"New product saved <{url}>")
                            
                except Exception as e:
                    print(f"Error processing link: {str(e)}")
                    await links_channel.send(
                        f"New link saved <{url}> from {message.author.mention}"
                    )
            # Remove loading messages
            for loading_message in loading_messages:
                await loading_message.delete()

    async def process_command(self, message):
        content = message.content.lower()
        
        # Handle channel exclusion commands
        if content.startswith("!help") or content.startswith("!commands"):
            command = message.content.split()[1].lstrip('!').lower() if len(message.content.split()) > 1 else None
            help_responses = {
                # General help
                None: """
**Reaction Commands:**
❌      -   Soft-deletes link from database and removes from #links.

**Available commands:**

**--- help ---**
`!help [command]`         -   Get help with a command.

**--- data manipulation ---**
`!categorized-links`      -   Get all active links grouped by categories.
`!display-links [-d]`     -   Displays all non-deleted links. Add -d flag to get deleted links as well.
`!restore <link_id>`      -   Restores deleted link by link_id. Get from !display-links -d

**--- exclude channel ---**
`!exclude <channel_id>`   -   Exclude a channel id.
`!list-excluded`          -   List excluded channel ids.
`!unexclude <channel_id>` -   Unexclude a channel id.""",

                # Core commands
                'help': """**Command Help**: `!help [command]`
- Displays general help or detailed command information
- Works with or without exclamation mark
- Example: `!help delete` or `!help !restore`""",

                # Data management commands
                'categorized-links': """**Command Help**: `!categorized-links`
- Displays active links organized by category
- Shows link ID, URL, and summary preview
- Format: Category header followed by list items
- Example: `!categorized-links`""",

                'display-links': """**Command Help**: `!display-links [-d]`
- Lists stored links with their status
- Add `-d` flag to include deleted links
- Shows link ID, URL, and deletion status
- Example: `!display-links` or `!display-links -d`""",

                'delete': """**Command Help**: `!delete <link_id>`
- Soft-deletes specified link (marks as deleted)
- Requires valid link ID from !display-links
- Deleted links can be restored
- Example: `!delete 42`""",

                'restore': """**Command Help**: `!restore <link_id>`
- Restores previously deleted link
- Requires link ID from !display-links -d
- Returns link to active status
- Example: `!restore 42`""",

                # Channel control commands
                'exclude': """**Command Help**: `!exclude <channel_id>`
- Adds channel to exclusion list
- Requires channel ID or mention
- Prevents link scanning in specified channel
- Example: `!exclude 123456789` or `!exclude #general`""",

                'list-excluded': """**Command Help**: `!list-excluded`
- Shows all excluded channels
- Displays channel mentions for easy identification
- Example: `!list-excluded`""",

                'unexclude': """**Command Help**: `!unexclude <channel_id>`
- Removes channel from exclusion list
- Requires existing excluded channel ID
- Re-enables link scanning in channel
- Example: `!unexclude 123456789`"""
            }

            response = help_responses.get(command, help_responses[None])
            if command and command not in help_responses:
                response = f"Command '{command}' not found. Try !help for general assistance"
            
            await message.channel.send(response)
            return

        if content.startswith("!exclude"):
            channel_id = self._extract_channel_id(message.content)
            if channel_id and self.exclusion_service.add_excluded_channel(channel_id):
                await message.channel.send(f"Channel <#{channel_id}> excluded from link scanning")
            return
        
        if content.startswith("!unexclude"):
            channel_id = self._extract_channel_id(message.content)
            if channel_id and self.exclusion_service.remove_excluded_channel(channel_id):
                await message.channel.send(f"Channel <#{channel_id}> removed from exclusion list")
            return
        
        if content.startswith("!list-excluded"):
            excluded = self.exclusion_service.get_excluded_channels()
            response = "**Excluded Channels**:\n" + "\n".join(
                [f"- <#{cid}>" for cid in excluded] or ["None"]
            )
            await message.channel.send(response)
            return
        
        if content.startswith("!categorized-links"):
            links = self.db.get_links_by_category()
            response = self.categorizer.format_categorized(links)
            await message.channel.send(response)
            return
        
        # Handle !display-links
        if content.startswith("!display-links"):
            include_deleted = '-d' in message.content.split()
            links = self.db.get_all_links(include_deleted=include_deleted)
            response = self._format_display_links(links)
            await message.channel.send(response)
            return
        
        # Handle !delete
        if content.startswith("!delete"):
            link_id = self._extract_link_id(message.content)
            if link_id is None:
                await message.channel.send("Invalid syntax. Use: `!delete <link_id>`")
                return
            success = self.db.delete_link(link_id)
            response = f"Link {link_id} {'deleted' if success else 'not found'}"
            await message.channel.send(response)
            return
        
        # Handle !restore
        if content.startswith("!restore"):
            link_id = self._extract_link_id(message.content)
            if link_id is None:
                await message.channel.send("Invalid syntax. Use: `!restore <link_id>`")
                return
            success = self.db.restore_link(link_id)
            response = f"Link {link_id} {'restored' if success else 'not found'}"
            await message.channel.send(response)
            return
        
        try:
            async with message.channel.typing():  # Show typing in command channel
                classification = await self.ai.classify_command(message.content)
                
                if not isinstance(classification, dict):
                    classification = {"command_type": "NONE"}
                    
                command_type = classification.get("command_type", "NONE")
                timeframe_days = classification.get("timeframe_days")
                max_results = classification.get("max_results")

                print(f"\n{' AI Context Package ':=^80}")
                print(f"Channel: {message.channel} ({message.channel.id})")
                print(f"Author:  {message.author} ({message.author.id})")
                print(f"Command: {message.content}")
                print(f"Classification: {classification}")

                if command_type == "NONE":
                    # Get adjustable number of context messages from config
                    context_messages = []
                    if message.channel.name == COMMAND_CHANNEL:
                        context_messages = await self.get_channel_context(
                            message.channel,
                            limit=CONTEXT_MESSAGE_COUNT
                        )
                    response = await self.ai.generate_response(message.content, context_messages)
                else:
                    links = self.db.get_recent_links(
                        days_ago=timeframe_days,
                        limit=max_results
                    )
                    print(f"Found {len(links)} relevant links:")
                    for link in links:
                        print(f"- [ID: {link.link_id}] {link.web_url}")

                    if not links:
                        response = "No relevant links found in my records."
                    else:
                        try:
                            context = await self._build_command_context(command_type, links, message.content)
                            print("\nContext sent to AI:")
                            for idx, item in enumerate(context, 1):
                                print(f"\nContext Item {idx}:")
                            print(f"{'-'*40}")
                            print(item.strip())
                            print(f"{'-'*40}")
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
                string += f"URL: <{link.web_url}> | "
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
                f"ID: {link.link_id} | URL: <{link.web_url}>\n"
                f"Fresh Content: {content[:1000] if content else 'Unable to retrieve content'}"
            )
        return context

    def _extract_channel_id(self, text: str) -> Optional[str]:
        match = re.search(r"<#(\d+)>", text)
        return match.group(1) if match else None
    
    def _extract_link_id(self, text: str) -> Optional[int]:
        parts = text.split()
        for part in parts[1:]:
            if part.isdigit():
                return int(part)
        return None
    
    def _extract_url_from_message(self, message: discord.Message) -> Optional[str]:
        """Extract URL from message content, handling > termination"""
        # Look for URL in message content
        match = re.search(r'https?://[^\s>]+', message.content)
        if not match:
            return None
        
        url = match.group(0)
        
        # Remove trailing > if present
        if url.endswith('>'):
            url = url[:-1]
        
        return url

    def _format_display_links(self, links: List[Link]) -> str:
        if not links:
            return "No links found."
        response = "**Links (ID | URL | Status)**\n"
        for link in links:
            status = "❌ Deleted" if link.deleted else "✅ Active"
            response += f"- `{link.link_id}`: <{link.web_url}> — {status}\n"
        return response[:2000]  # Truncate to Discord's message limit

def main():
    db = DBClient()
    ai = OpenAIClient()
    bot = LinkBot(db, ai)
    bot.run(DISCORD_TOKEN)
