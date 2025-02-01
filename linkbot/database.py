import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
from typing import Optional, List
from linkbot.models import Link

class DBClient:
    def __init__(self, config):
        self.config = config
        # self._create_tables()
    
    @contextmanager
    def _get_connection(self):
        conn = mysql.connector.connect(**self.config)
        try:
            yield conn
        finally:
            conn.close()
    
    def save_link(self, web_url: str, summary: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO links (web_url, summary)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE summary=VALUES(summary)
                """, (web_url, summary))
                conn.commit()
                return cursor.lastrowid
            except Error as e:
                print(f"Error saving link: {e}")
                return -1
    
    def get_link(self, web_url: str) -> Optional[Link]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM links 
                WHERE web_url = %s AND is_active = TRUE
            """, (web_url,))
            result = cursor.fetchone()
            return Link(**result) if result else None
    
    def soft_delete_link(self, link_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE links SET is_active = FALSE 
                WHERE link_id = %s
            """, (link_id,))
            conn.commit()
    
    def get_recent_links(self, days_ago: int = None, limit: int = None) -> list[Link]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM links WHERE is_active = TRUE"
            params = []
            
            if days_ago:
                query += " AND creation_date >= DATE_SUB(NOW(), INTERVAL %s DAY)"
                params.append(days_ago)
            
            query += " ORDER BY creation_date DESC"
            
            if limit:
                query += " LIMIT %s"
                params.append(limit)
            
            cursor.execute(query, params)
            return [Link(**row) for row in cursor.fetchall()]
    
    # In database.py
    def get_link_by_id(self, link_id: int) -> Optional[Link]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM links 
                WHERE link_id = %s AND is_active = TRUE
            """, (link_id,))
            result = cursor.fetchone()
            return Link(**result) if result else None

    def update_link_summary(self, link_id: int, summary: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE links SET summary = %s 
                WHERE link_id = %s
            """, (summary, link_id))
            conn.commit()
    
    # In database.py
    def get_recent_links(self, days_ago: int = None, limit: int = None) -> list[Link]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM links WHERE is_active = TRUE"
            params = []
            
            if days_ago:
                query += " AND creation_date >= DATE_SUB(NOW(), INTERVAL %s DAY)"
                params.append(days_ago)
            
            query += " ORDER BY creation_date DESC"
            
            if limit:
                query += " LIMIT %s"
                params.append(limit)
            
            cursor.execute(query, params)
            return [Link(**row) for row in cursor.fetchall()]