# Discord Link Manager Bot

A sophisticated Discord bot for managing, categorizing, and organizing shared links with AI-powered summarization and duplicate handling.

## Features

- **Automatic Link Capture**: Detects and processes URLs shared in channels
- **AI-Powered Summarization**: Generates concise summaries using DeepSeek AI
- **Smart Categorization**: Automatically categorizes links into 20+ topics
- **Version Control**: Handles duplicates by archiving old versions
- **Reaction Controls**: Delete links with ❌ reaction (Manage Messages permission required)
- **Channel Exclusion**: Manage monitored channels via commands
- **Soft Deletion**: Maintains history while keeping channels clean
- **Search**: Find links by category/time/relevance using natural language

## Commands

### Help
!help [command] - Detailed command help

### Data Management
!categorized-links - View links grouped by category
!display-links [-d] - Show active links (-d includes deleted)
!delete <link_id> - Delete specific link
!restore <link_id> - Restore deleted link

### Channel Controls
!exclude <channel> - Exclude channel from scanning
!list-excluded - Show excluded channels
!unexclude <channel> - Remove channel exclusion

## Installation

1. **Clone Repository**
  ```bash
  git clone https://github.com/yourusername/discord-link-bot.git
  cd discord-link-bot
  ```

2. **Install Dependencies**
  ```bash
  pip install -r requirements.txt
  ```

3. **Configure Settings**
  ```python
  # config.py
  DISCORD_TOKEN = 'your_bot_token'
  OPENROUTER_API_KEY = 'your_api_key'
  DB_CONFIG = {
      'host': 'localhost',
      'user': 'db_user',
      'password': 'db_pass',
      'database': 'link_bot_db'
  }
  ```

4. **Initialize Database**
  ```bash
  python -c "from database import DBClient; DBClient(DB_CONFIG)._create_tables()"
  ```

5. **Start Bot**
  ```bash
  python -m linkbot
  ```

Database Schema

Links Table

Column	Type	Description
link_id	INT	Primary key
web_url	VARCHAR(2048)	Original URL
summary	TEXT	AI-generated summary
category	VARCHAR(255)	Auto-assigned category
creation_date	DATETIME	Timestamp of creation
deleted	BOOLEAN	Soft deletion flag
ExcludedChannels

Column	Type	Description
channel_id	VARCHAR	Discord channel ID
created_at	DATETIME	Exclusion timestamp
Deployment

**Docker**
```bash
docker build -t link-bot .
docker run -d --name link-bot \
  -e DISCORD_TOKEN=your_token \
  -e OPENROUTER_API_KEY=your_key \
  -e DB_HOST=db_host \
  link-bot
```

**Systemd Service**
```ini
# /etc/systemd/system/link-bot.service
[Unit]
Description=Discord Link Bot
After=network.target

[Service]
User=botuser
ExecStart=/usr/bin/python3 -m linkbot
Restart=always
Environment=DISCORD_TOKEN=your_token
Environment=OPENROUTER_API_KEY=your_key
```

### Workflow

User shares URL in non-excluded channel
Bot scrapes content and generates summary/category
Checks for existing active links:
New: New link saved [URL] from @user
Duplicate: Duplicate link updated [URL] from @user
Messages appear in dedicated links channel
Moderators can ❌ react to delete messages+links
