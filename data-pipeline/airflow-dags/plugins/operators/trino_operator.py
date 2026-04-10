from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.models import Variable
import logging
import trino

logger = logging.getLogger(__name__)

class TrinoOperator(BaseOperator):
    """
    Custom Airflow operator for running Trino SQL queries
    """
    
    template_fields = ['sql']
    template_ext = ['.sql']
    ui_color = '#13a8e2'
    
    @apply_defaults
    def __init__(self, sql, trino_conn_id='trino_default', **kwargs):
        super(TrinoOperator, self).__init__(**kwargs)
        self.sql = sql
        self.trino_conn_id = trino_conn_id
        self.results = None
    
    def execute(self, context):
        logger.info(f"Executing Trino query:\n{self.sql}")
        
        trino_host = Variable.get("TRINO_HOST", "trino")
        trino_port = int(Variable.get("TRINO_PORT", "8080"))
        trino_user = Variable.get("TRINO_USER", "trino")
        trino_catalog = Variable.get("TRINO_CATALOG", "iceberg")
        trino_schema = Variable.get("TRINO_SCHEMA", "default")
        
        try:
            conn = trino.dbapi.connect(
                host=trino_host,
                port=trino_port,
                user=trino_user,
                catalog=trino_catalog,
                schema=trino_schema,
            )
            
            cursor = conn.cursor()
            cursor.execute(self.sql)
            
            self.results = cursor.fetchall()
            
            logger.info(f"Query executed successfully, returned {len(self.results) if self.results else 0} rows")
            
            cursor.close()
            conn.close()
            
            return self.results
        
        except Exception as e:
            logger.error(f"Error executing Trino query: {e}")
            raise
    
    def get_results(self):
        return self.results
