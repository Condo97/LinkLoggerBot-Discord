# channel_exclusion.py
from datetime import datetime
from mysql.connector import Error

class ChannelExclusionService:
    def __init__(self, db_client):
        self.db = db_client

    def add_excluded_channel(self, channel_id: str) -> bool:
        """Add a channel to exclusion list"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ExcludedChannels (channel_id, created_at)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE channel_id=channel_id
                """, (channel_id, datetime.now()))
                conn.commit()
                return cursor.rowcount > 0
        except Error as e:
            print(f"Error excluding channel: {e}")
            return False

    def remove_excluded_channel(self, channel_id: str) -> bool:
        """Remove a channel from exclusion list"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM ExcludedChannels 
                    WHERE channel_id = %s
                """, (channel_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Error as e:
            print(f"Error unexcluding channel: {e}")
            return False

    def get_excluded_channels(self) -> list[str]:
        """Get all excluded channel IDs"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT channel_id FROM ExcludedChannels")
                return [row['channel_id'] for row in cursor.fetchall()]
        except Error as e:
            print(f"Error fetching excluded channels: {e}")
            return []