# database.py
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
from typing import Optional, List
from linkbot.models import Link
from datetime import datetime


class DBClient:
    def __init__(self, config):
        self.config = config
        self._create_table()  # Initialize table on startup

    @contextmanager
    def _get_connection(self):
        conn = mysql.connector.connect(**self.config)
        try:
            yield conn
        finally:
            conn.close()

    def _create_table(self):
        """Create the links table if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS links (
                        link_id INT AUTO_INCREMENT PRIMARY KEY,
                        web_url VARCHAR(2048) NOT NULL,
                        summary TEXT NOT NULL,
                        creation_date DATETIME NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE
                    ) ENGINE=InnoDB;
                """)
                conn.commit()
            except Error as e:
                print(f"Error creating table: {e}")
                conn.rollback()

    def save_link(self, web_url: str, summary: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO links (web_url, summary, creation_date, is_active)
                    VALUES (%s, %s, %s, %s)
                """, (web_url, summary, datetime.now(), True))
                conn.commit()
                return cursor.lastrowid
            except Error as e:
                print(f"Error saving link: {e}")
                conn.rollback()
                return -1

    def get_recent_links(self, days_ago: int = None, limit: int = None) -> list[Link]:
        query = """SELECT * FROM Links 
                   WHERE is_active = TRUE"""
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

    def get_links_by_ids(self, link_ids: list[int]) -> list[Link]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM Links 
                WHERE link_id IN (%s)
                """ % ','.join(['%s']*len(link_ids)),
                tuple(link_ids))
            return [Link(**row) for row in cursor.fetchall()]