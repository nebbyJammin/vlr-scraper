import os
from psycopg2 import pool
from psycopg2.pool import ThreadedConnectionPool
from logging_config import PG_LOGGER as LOGGER

class PostgresPool:
    _instance = None # Singleton Instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        
        return cls._instance
    
    def __init__(self):
        # Load from environment
        DB_HOST=os.getenv("DB_HOST", "localhost")
        DB_PORT=os.getenv("DB_PORT", 5432)
        DB_NAME=os.getenv("DB_NAME", "mydb")
        DB_USER=os.getenv("DB_USER", "myuser")
        DB_PASSWORD=os.getenv("DB_PASSWORD", "mypassword")

        self._pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )

        LOGGER.info("Successfully created PostgresPool object")
    
    def get_conn(self):
        """Get a connection from the pool"""
        return self._pool.getconn()
    
    def put_conn(self, conn):
        """Return a connection to the pool"""
        self._pool.putconn(conn)
    
    def close_all(self):
        """Close all connections"""
        self._pool.closeall()