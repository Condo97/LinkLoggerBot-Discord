# database.py
import os
import mysql.connector
from mysql.connector import Error, pooling
from contextlib import contextmanager
from typing import Optional, List
from linkbot.models import Link
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential


class DBClient:
    def __init__(self):
        self.config = {
            'host': os.getenv('DB_HOST'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_SCHEMA')
        }
        self.pool = pooling.MySQLConnectionPool(
            pool_name="bot_pool",
            pool_size=5,
            pool_reset_session=True,
            **self.config
        )
        self._create_tables()  # Initialize table on startup

    @contextmanager
    def _get_connection(self):
        conn = self.pool.get_connection()
        try:
            if not conn.is_connected():
                conn.reconnect(attempts=3, delay=5)
            yield conn
        finally:
            conn.close()
    
    def _create_tables(self):
        """Create required tables on startup"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Create Links table with category
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS Links (
                        link_id INT AUTO_INCREMENT PRIMARY KEY,
                        web_url VARCHAR(2048) NOT NULL,
                        summary TEXT NOT NULL,
                        category VARCHAR(255) NOT NULL,
                        creation_date DATETIME NOT NULL,
                        deleted BOOLEAN NOT NULL DEFAULT TRUE
                    ) ENGINE=InnoDB;
                """)
                
                # Create ExcludedChannels table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ExcludedChannels (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        channel_id VARCHAR(255) NOT NULL UNIQUE,
                        created_at DATETIME NOT NULL
                    ) ENGINE=InnoDB;
                """)
                conn.commit()
            except Error as e:
                print(f"Error creating tables: {e}")
                conn.rollback()

    # Add category to save_link method
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def save_link(self, web_url: str, summary: str, category: str) -> int:
        """Save new link or update existing one"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Check for existing active link
                cursor.execute("""
                    SELECT link_id FROM Links 
                    WHERE web_url = %s AND deleted = FALSE
                    LIMIT 1
                """, (web_url,))
                existing = cursor.fetchone()
                
                if existing:
                    # Mark existing as deleted
                    cursor.execute("""
                        UPDATE Links 
                        SET deleted = TRUE 
                        WHERE link_id = %s
                    """, (existing[0],))
                
                # Insert new link
                cursor.execute("""
                    INSERT INTO Links (web_url, summary, category, creation_date, deleted)
                    VALUES (%s, %s, %s, %s, %s)
                """, (web_url, summary, category, datetime.now(), False))
                
                conn.commit()
                return cursor.lastrowid
            except Error as e:
                print(f"Error saving link: {e}")
                conn.rollback()
                return -1

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def get_links_by_category(self) -> dict:
        """Get all links grouped by category"""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT category, web_url, summary, link_id
                FROM Links 
                WHERE deleted = FALSE
                ORDER BY creation_date DESC
            """)
            categorized = {}
            for row in cursor.fetchall():
                category = row['category']
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(row)
            return categorized
        
    def get_links_by_ids(self, link_ids: list[int]) -> list[Link]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM Links 
                WHERE link_id IN (%s)
                """ % ','.join(['%s']*len(link_ids)),
                tuple(link_ids))
            return [Link(**row) for row in cursor.fetchall()]
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def get_link_by_url(self, url: str) -> Optional[Link]:
        """Find an active link by its URL"""
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT * FROM Links 
                    WHERE web_url = %s 
                    AND deleted = FALSE
                    ORDER BY creation_date DESC
                    LIMIT 1
                """, (url,))
                result = cursor.fetchone()
                return Link(**result) if result else None
            except Error as e:
                print(f"Error finding link by URL: {e}")
                return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def get_all_links(self, include_deleted: bool = False) -> list[Link]:
        """Retrieve all links, optionally including deleted ones."""
        query = "SELECT * FROM Links"
        params = []
        if not include_deleted:
            query += " WHERE deleted = %s"
            params.append(False)
        query += " ORDER BY creation_date DESC"
        
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            return [Link(**row) for row in cursor.fetchall()]

    def delete_link(self, link_id: int) -> bool:
        """Soft delete a link by marking deleted as True."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE Links 
                    SET deleted = TRUE 
                    WHERE link_id = %s
                """, (link_id,))
                conn.commit()
                return cursor.rowcount > 0
            except Error as e:
                print(f"Error deleting link: {e}")
                conn.rollback()
                return False

    def restore_link(self, link_id: int) -> bool:
        """Restore a soft-deleted link by marking deleted as False."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE Links 
                    SET deleted = FALSE 
                    WHERE link_id = %s
                """, (link_id,))
                conn.commit()
                return cursor.rowcount > 0
            except Error as e:
                print(f"Error restoring link: {e}")
                conn.rollback()
                return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def get_recent_links(self, days_ago: int = None, limit: int = None) -> list[Link]:
        query = """SELECT * FROM Links 
                   WHERE deleted = FALSE"""
        params = []
        
        if days_ago is not None:
            query += " AND creation_date >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL %s DAY)"
            params.append(days_ago)
        
        query += " ORDER BY creation_date DESC"
        
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            return [Link(**row) for row in cursor.fetchall()]
