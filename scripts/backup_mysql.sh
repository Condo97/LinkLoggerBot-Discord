#!/bin/bash

# Variables
DB_NAME="linkbotschema”
DB_USER="linkbotconnection”
DB_PASS="LinkBotConnection1!!!”
BACKUP_DIR="/LinkLoggerBot/backups"
DATE=$(date +"%Y%m%d%H%M%S")

# Create backup
mysqldump -u $DB_USER -p$DB_PASS $DB_NAME > $BACKUP_DIR/$DB_NAME-$DATE.sql

# Compress backup
gzip $BACKUP_DIR/$DB_NAME-$DATE.sql

# Delete backups older than 7 days
find $BACKUP_DIR -name "$DB_NAME-*.sql.gz" -type f -mtime +7 -exec rm {} \;

—  Commands
chmod +x /path/to/backup_mysql.sh
crontab -e
0 2 * * * /path/to/backup_mysql.sh
0 14 * * * /path/to/backup_mysql.sh