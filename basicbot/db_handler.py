"""
-- D:\\TradingRobotPlug\\basicbot\\db_handler.py --

Description:
------------
This module provides a unified interface for interacting with a database,
supporting PostgreSQL and MySQL as backends. Database credentials and other
configuration settings are obtained from the centralized configuration (config.py).
Use this module to store and retrieve scraped social media posts.

Usage Example:
    from basicbot.db_handler import DatabaseHandler
    db = DatabaseHandler(logger)
    db.save_posts(posts)
    results = db.fetch_posts(limit=10)
    db.close()
"""

import logging
from basicbot.config import config
from setup_logging import setup_logging

# Import database connectors
import psycopg2
import mysql.connector

class DatabaseHandler:
    """
    Unified database handler for storing scraped posts.
    Supports PostgreSQL and MySQL based on the DB_TYPE configuration.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        # Retrieve the DB_TYPE from configuration; default to PostgreSQL if not set.
        self.db_type = config.get_env("DB_TYPE", "postgresql").lower()

        if self.db_type not in {"postgresql", "mysql"}:
            raise ValueError(f"Unsupported database type: {self.db_type}. Only 'postgresql' and 'mysql' are supported.")

        self.logger.info("Initializing DatabaseHandler for %s", self.db_type)

        if self.db_type == "postgresql":
            self.conn = psycopg2.connect(
                dbname=config.get_env("POSTGRES_DBNAME"),
                user=config.get_env("POSTGRES_USER"),
                password=config.get_env("POSTGRES_PASSWORD"),
                host=config.get_env("POSTGRES_HOST", "localhost"),
                port=config.get_env("POSTGRES_PORT", 5432, int)
            )
        elif self.db_type == "mysql":
            self.conn = mysql.connector.connect(
                database=config.get_env("MYSQL_DB_NAME"),
                user=config.get_env("MYSQL_DB_USER"),
                password=config.get_env("MYSQL_DB_PASSWORD"),
                host=config.get_env("MYSQL_DB_HOST", "localhost"),
                port=config.get_env("MYSQL_DB_PORT", 3306, int)
            )
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()
        self._initialize_table()

    def _initialize_table(self):
        """
        Initializes the posts table if it does not exist.
        The table schema includes columns for id, platform, text, link, and timestamp.
        """
        if self.db_type == "postgresql":
            create_table_query = """
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                platform VARCHAR(50),
                text TEXT,
                link TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        elif self.db_type == "mysql":
            create_table_query = """
            CREATE TABLE IF NOT EXISTS posts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                platform VARCHAR(50),
                text TEXT,
                link TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        try:
            self.cursor.execute(create_table_query)
            self.logger.info("Posts table initialized successfully.")
        except Exception as e:
            self.logger.error("Error initializing posts table: %s", e)

    def save_posts(self, posts):
        """
        Saves a list of post dictionaries into the database.
        
        Each post should be a dictionary with keys: 'platform', 'text', and optionally 'link'.
        
        :param posts: List of dictionaries containing post data.
        """
        if not posts:
            self.logger.info("No posts to save.")
            return

        insert_query = "INSERT INTO posts (platform, text, link) VALUES (%s, %s, %s);"
        for post in posts:
            try:
                data_tuple = (post.get("platform"), post.get("text"), post.get("link"))
                self.cursor.execute(insert_query, data_tuple)
            except Exception as e:
                self.logger.error("Error saving post: %s", e)
        self.conn.commit()
        self.logger.info("Saved %d posts.", len(posts))

    def fetch_posts(self, limit=10):
        """
        Fetches the most recent posts from the database.
        
        :param limit: Maximum number of posts to fetch.
        :return: List of posts as dictionaries.
        """
        query = "SELECT id, platform, text, link, timestamp FROM posts ORDER BY timestamp DESC LIMIT %s;"
        try:
            self.cursor.execute(query, (limit,))
            rows = self.cursor.fetchall()
            posts = []
            for row in rows:
                posts.append({
                    "id": row[0],
                    "platform": row[1],
                    "text": row[2],
                    "link": row[3],
                    "timestamp": row[4]
                })
            return posts
        except Exception as e:
            self.logger.error("Error fetching posts: %s", e)
            return []

    def close(self):
        """
        Closes the database connection.
        """
        self.cursor.close()
        self.conn.close()
        self.logger.info("Database connection closed.")

# Example usage when running the module directly
if __name__ == "__main__":
    # Initialize logger using the centralized logging configuration
    logger = setup_logging("db_handler", log_dir=config.get_env("LOG_DIR", "logs/db"))
    try:
        db = DatabaseHandler(logger)
        # Example: Save dummy posts
        sample_posts = [
            {"platform": "Twitter", "text": "Test tweet content", "link": "https://twitter.com/example"},
            {"platform": "LinkedIn", "text": "Test LinkedIn post", "link": None}
        ]
        db.save_posts(sample_posts)
        fetched = db.fetch_posts(limit=5)
        logger.info("Fetched posts: %s", fetched)
    except Exception as e:
        logger.error("Error in DatabaseHandler usage: %s", e)
    finally:
        db.close()
