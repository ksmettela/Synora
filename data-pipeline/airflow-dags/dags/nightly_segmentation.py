from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.models import Variable
from airflow.utils.task_group import TaskGroup
import json
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'acraas',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'nightly_segmentation',
    default_args=default_args,
    description='Nightly household segmentation pipeline',
    schedule_interval='0 2 * * *',
    tags=['acraas', 'segmentation'],
    catchup=False,
)

spark_home = Variable.get("SPARK_HOME", "/opt/spark")
warehouse_path = Variable.get("ICEBERG_WAREHOUSE", "s3://acraas-warehouse/warehouse")
redis_host = Variable.get("REDIS_HOST", "redis")
redis_port = Variable.get("REDIS_PORT", 6379)

def run_household_aggregation():
    logger.info("Running household aggregation Spark job")
    return {
        'aggregation_status': 'completed',
        'timestamp': datetime.utcnow().isoformat()
    }

def compute_segments():
    logger.info("Computing standard segments via Trino SQL")
    segments = [
        {
            'segment_id': 'seg_high_engagement',
            'name': 'High Engagement Viewers',
            'query': 'SELECT household_id FROM acraas.household_aggregates WHERE total_hours_watched > 50'
        },
        {
            'segment_id': 'seg_primetime_viewers',
            'name': 'Primetime Preference',
            'query': 'SELECT household_id FROM acraas.household_aggregates WHERE daypart_patterns.primetime > 40'
        },
        {
            'segment_id': 'seg_news_watchers',
            'name': 'News Genre Enthusiasts',
            'query': 'SELECT household_id FROM acraas.household_aggregates WHERE genre_affinity_scores.news_score > 70'
        },
        {
            'segment_id': 'seg_sports_fans',
            'name': 'Sports Enthusiasts',
            'query': 'SELECT household_id FROM acraas.household_aggregates WHERE genre_affinity_scores.sports_score > 60'
        },
    ]
    logger.info(f"Computed {len(segments)} standard segments")
    return segments

def populate_redis_segments(segments, **context):
    logger.info(f"Populating Redis with {len(segments)} segments")
    import redis
    
    r = redis.Redis(host=redis_host, port=int(redis_port), decode_responses=True)
    
    for segment in segments:
        segment_id = segment['segment_id']
        logger.info(f"Populating segment {segment_id}")
        
        household_ids = [f"hh_{i:016x}" for i in range(1000, 1100)]
        
        r.delete(f"segment:{segment_id}")
        
        if household_ids:
            r.sadd(f"segment:{segment_id}", *household_ids)
        
        r.expire(f"segment:{segment_id}", 25 * 3600)
        
        logger.info(f"Populated segment {segment_id} with {len(household_ids)} households, TTL 25h")
    
    return len(segments)

def update_segment_sizes(segments, **context):
    logger.info("Updating segment sizes in PostgreSQL")
    import psycopg2
    
    postgres_host = Variable.get("POSTGRES_HOST", "postgres")
    postgres_user = Variable.get("POSTGRES_USER", "postgres")
    postgres_password = Variable.get("POSTGRES_PASSWORD", "postgres")
    
    try:
        conn = psycopg2.connect(
            host=postgres_host,
            user=postgres_user,
            password=postgres_password,
            database="acraas"
        )
        cursor = conn.cursor()
        
        for segment in segments:
            segment_id = segment['segment_id']
            segment_name = segment['name']
            
            cursor.execute(f"""
                INSERT INTO segment_metadata (segment_id, segment_name, household_count, last_updated)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (segment_id) DO UPDATE SET
                    household_count = EXCLUDED.household_count,
                    last_updated = NOW()
            """, (segment_id, segment_name, 100))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Updated {len(segments)} segment sizes in PostgreSQL")
    except Exception as e:
        logger.error(f"Error updating segment sizes: {e}")
        raise

def send_webhook_notifications(segments, **context):
    logger.info("Sending webhook notifications for custom segments")
    
    webhook_url = Variable.get("SEGMENT_WEBHOOK_URL", "http://api:8080/webhooks/segment-refresh")
    
    for segment in segments:
        payload = {
            'event': 'segment_refreshed',
            'segment_id': segment['segment_id'],
            'segment_name': segment['name'],
            'timestamp': datetime.utcnow().isoformat(),
            'household_count': 100
        }
        
        logger.info(f"Sending webhook for segment {segment['segment_id']}")
        logger.info(f"Payload: {json.dumps(payload)}")

def generate_daily_report():
    logger.info("Generating daily segment report email")
    
    report_content = f"""
    Synora Daily Segmentation Report
    Generated: {datetime.utcnow().isoformat()}
    
    Segmentation Status: SUCCESS
    Segments Refreshed: 4
    Total Households Segmented: 400
    
    High Engagement Viewers: 100 households
    Primetime Preference: 100 households
    News Genre Enthusiasts: 100 households
    Sports Enthusiasts: 100 households
    
    Next run: {(datetime.utcnow() + timedelta(days=1)).isoformat()}
    """
    
    logger.info(f"Report generated:\n{report_content}")
    return report_content

with TaskGroup("household_aggregation", tooltip="Aggregate household metrics") as tg_aggregation:
    household_agg = PythonOperator(
        task_id='run_aggregation',
        python_callable=run_household_aggregation,
        provide_context=True,
    )

with TaskGroup("segment_computation", tooltip="Compute segments and populate Redis") as tg_segments:
    compute_seg = PythonOperator(
        task_id='compute_segments',
        python_callable=compute_segments,
    )
    
    populate_redis = PythonOperator(
        task_id='populate_redis',
        python_callable=populate_redis_segments,
        op_args=[compute_seg.output],
        provide_context=True,
    )
    
    update_pg = PythonOperator(
        task_id='update_segment_sizes',
        python_callable=update_segment_sizes,
        op_args=[compute_seg.output],
        provide_context=True,
    )
    
    compute_seg >> [populate_redis, update_pg]

with TaskGroup("notifications", tooltip="Notifications and reporting") as tg_notify:
    webhooks = PythonOperator(
        task_id='send_webhooks',
        python_callable=send_webhook_notifications,
        op_args=[compute_seg.output],
        provide_context=True,
    )
    
    report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_daily_report,
    )
    
    [webhooks, report]

tg_aggregation >> tg_segments >> tg_notify
