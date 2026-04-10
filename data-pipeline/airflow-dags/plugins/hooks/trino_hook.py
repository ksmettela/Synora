from airflow.hooks.base import BaseHook
from airflow.models import Connection
import logging
import trino

logger = logging.getLogger(__name__)

class TrinoHook(BaseHook):
    """
    Hook to interact with Trino database
    """
    
    def __init__(self, trino_conn_id='trino_default'):
        self.trino_conn_id = trino_conn_id
        self.conn = None
        self._connection = None
    
    def get_conn(self):
        """
        Returns a Trino connection object
        """
        if self.conn is not None:
            return self.conn
        
        connection = BaseHook.get_connection(self.trino_conn_id)
        
        host = connection.host or 'trino'
        port = connection.port or 8080
        user = connection.login or 'trino'
        password = connection.password
        catalog = connection.extra_dejson.get('catalog', 'iceberg')
        schema = connection.extra_dejson.get('schema', 'default')
        
        logger.info(f"Connecting to Trino at {host}:{port}")
        
        self.conn = trino.dbapi.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            catalog=catalog,
            schema=schema,
        )
        
        return self.conn
    
    def get_cursor(self):
        """
        Returns a cursor to the Trino connection
        """
        return self.get_conn().cursor()
    
    def execute(self, sql, fetch_all=False):
        """
        Executes SQL query and returns results
        """
        cursor = self.get_cursor()
        logger.info(f"Executing SQL:\n{sql}")
        
        try:
            cursor.execute(sql)
            
            if fetch_all:
                result = cursor.fetchall()
            else:
                result = cursor.fetchone()
            
            return result
        finally:
            cursor.close()
    
    def execute_and_get_all(self, sql):
        """
        Executes SQL query and returns all results
        """
        return self.execute(sql, fetch_all=True)
    
    def close(self):
        """
        Closes the Trino connection
        """
        if self.conn is not None:
            self.conn.close()
            self.conn = None
