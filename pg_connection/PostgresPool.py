import os
import socket
from psycopg2 import pool
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extensions import connection
from logging_config import PG_LOGGER as LOGGER
from sshtunnel import SSHTunnelForwarder

class PostgresPool:
    _instance = None # Singleton Instance
    _tunnel = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        
        return cls._instance
    
    def __init__(self):
        # Load DB settings from environment
        self.DB_HOST=os.getenv("DB_HOST", "localhost")
        self.DB_PORT=os.getenv("DB_PORT", 5432)
        self.DB_NAME=os.getenv("DB_NAME", "mydb")
        self.DB_USER=os.getenv("DB_USER", "myuser")
        self.DB_PASSWORD=os.getenv("DB_PASSWORD", "mypassword")

        # Load SSH tunnel settings from environment
        self.SSH_USE_TUNNEL=os.getenv("SSH_USE_DB_TUNNEL", "false").lower() in ("true", "1", "yes")
        self.SSH_TUNNELED_PORT=int(os.getenv('SSH_DB_TUNNELED_PORT', 6543))
        self.SSH_HOST=os.getenv("SSH_DB_HOST")
        self.SSH_USER=os.getenv("SSH_DB_USER")
        self.SSH_KEY=os.getenv("SSH_DB_KEY")

        # Intitiate the SSH tunnel if the user has enabled SSH tunnel
        if self.SSH_USE_TUNNEL:
            self._start_tunnel()
        
        self._init_pool()
    
    def _init_pool(self):
        self._pool: ThreadedConnectionPool = ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            user=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME
        )

        LOGGER.info("Postgres connection pool created")

    def _start_tunnel(self):
        if self._tunnel and self._tunnel.is_active: 
            return # already running

        if not self.SSH_HOST:
            LOGGER.error("No SSH Host specified in the .env - couldn't create ssh tunnel", exc_info=True)
            exit(1)
            
        if not self.SSH_USER:
            LOGGER.error("No SSH User specified in the .env - couldn't create ssh tunnel", exc_info=True)
            exit(1)

        LOGGER.warning("Starting SSH tunnel to %s", self.SSH_HOST)
        self._tunnel = SSHTunnelForwarder(
            (self.SSH_HOST, 22),
            ssh_username=self.SSH_USER,
            ssh_pkey=self.SSH_KEY,
            remote_bind_address=(self.DB_HOST, self.DB_PORT),
            local_bind_address=('localhost', self.SSH_TUNNELED_PORT),
        )
        self._tunnel.start()
        LOGGER.info("SSH tunnel established at localhost:%s", self._tunnel.local_bind_port)

        self.DB_HOST = 'localhost' # use localhost db_host since localhost:$local_bind_port is being tunneled to localhost:$DB_PORT on DB_HOST
        self.DB_PORT = self._tunnel.local_bind_port
    
    def _check_tunnel(self):
        if not self.SSH_USE_TUNNEL:
            return
        
        if not self._tunnel or not self._tunnel.is_active:
            LOGGER.error("SSH tunnel lost, restarting...", exc_info=True)
            self._start_tunnel()
            self._init_pool()
        
        else:
            try:
                with socket.create_connection(("localhost", self._tunnel.local_bind_port), timeout=2):
                    pass
            except Exception:
                LOGGER.error("SSH tunnel socket dead, restarting...", exc_info=True)
                self._start_tunnel()
                self._init_pool()
    
    def get_conn(self) -> connection:
        """Get a connection from the pool"""
        self._check_tunnel() # Check tunnel, will not do anything if we are not using tunnel
        return self._pool.getconn()
    
    def put_conn(self, conn):
        """Return a connection to the pool"""
        self._pool.putconn(conn)
    
    def close_all(self):
        """Close all connections"""
        self._pool.closeall()