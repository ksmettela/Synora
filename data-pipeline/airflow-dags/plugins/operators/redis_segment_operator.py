from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.models import Variable
import logging
import redis
import trino

logger = logging.getLogger(__name__)

class RedisSegmentOperator(BaseOperator):
    """
    Custom Airflow operator for populating Redis segment sets
    
    Takes a segment_id, Trino SQL query, and Redis TTL
    Runs the Trino query to get device_ids and populates Redis set
    """
    
    template_fields = ['segment_id', 'sql_query']
    ui_color = '#e74c3c'
    
    @apply_defaults
    def __init__(self, segment_id, sql_query, redis_ttl_hours=25, batch_size=1000, **kwargs):
        super(RedisSegmentOperator, self).__init__(**kwargs)
        self.segment_id = segment_id
        self.sql_query = sql_query
        self.redis_ttl_hours = redis_ttl_hours
        self.batch_size = batch_size
        self.populated_count = 0
    
    def execute(self, context):
        logger.info(f"Populating Redis segment: {self.segment_id}")
        logger.info(f"Query: {self.sql_query}")
        
        redis_host = Variable.get("REDIS_HOST", "redis")
        redis_port = int(Variable.get("REDIS_PORT", 6379))
        redis_db = int(Variable.get("REDIS_DB", 0))
        
        trino_host = Variable.get("TRINO_HOST", "trino")
        trino_port = int(Variable.get("TRINO_PORT", "8080"))
        trino_user = Variable.get("TRINO_USER", "trino")
        trino_catalog = Variable.get("TRINO_CATALOG", "iceberg")
        trino_schema = Variable.get("TRINO_SCHEMA", "default")
        
        try:
            redis_conn = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True
            )
            
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
            
            trino_conn = trino.dbapi.connect(
                host=trino_host,
                port=trino_port,
                user=trino_user,
                catalog=trino_catalog,
                schema=trino_schema,
            )
            
            cursor = trino_conn.cursor()
            logger.info(f"Connected to Trino at {trino_host}:{trino_port}")
            
            logger.info(f"Executing query to fetch device IDs for segment {self.segment_id}")
            cursor.execute(self.sql_query)
            
            segment_key = f"segment:{self.segment_id}"
            
            redis_conn.delete(segment_key)
            logger.info(f"Cleared existing segment key: {segment_key}")
            
            device_ids = []
            batch_count = 0
            
            for row in cursor:
                device_id = row[0] if isinstance(row, tuple) else row
                device_ids.append(str(device_id))
                
                if len(device_ids) >= self.batch_size:
                    redis_conn.sadd(segment_key, *device_ids)
                    batch_count += 1
                    logger.info(f"Batch {batch_count}: Added {len(device_ids)} device IDs to segment")
                    device_ids = []
            
            if device_ids:
                redis_conn.sadd(segment_key, *device_ids)
                batch_count += 1
                logger.info(f"Batch {batch_count}: Added {len(device_ids)} device IDs to segment")
            
            self.populated_count = redis_conn.scard(segment_key)
            
            ttl_seconds = self.redis_ttl_hours * 3600
            redis_conn.expire(segment_key, ttl_seconds)
            
            logger.info(f"Successfully populated segment {self.segment_id}")
            logger.info(f"Total households in segment: {self.populated_count}")
            logger.info(f"TTL set to {self.redis_ttl_hours} hours ({ttl_seconds} seconds)")
            
            cursor.close()
            trino_conn.close()
            redis_conn.close()
            
            return {
                'segment_id': self.segment_id,
                'household_count': self.populated_count,
                'ttl_hours': self.redis_ttl_hours,
                'status': 'success'
            }
        
        except Exception as e:
            logger.error(f"Error populating Redis segment {self.segment_id}: {e}")
            raise
    
    def get_populated_count(self):
        return self.populated_count
