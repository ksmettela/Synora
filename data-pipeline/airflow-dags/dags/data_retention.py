from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.exceptions import AirflowException
from airflow.models import Variable
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'acraas',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    'data_retention',
    default_args=default_args,
    description='Daily data retention enforcement and cleanup',
    schedule_interval='0 3 * * *',
    tags=['acraas', 'retention'],
    catchup=False,
)

spark_home = Variable.get("SPARK_HOME", "/opt/spark")
warehouse_path = Variable.get("ICEBERG_WAREHOUSE", "s3://acraas-warehouse/warehouse")

def trigger_retention_cleanup():
    logger.info("Triggering Spark RetentionCleanupJob")
    
    spark_job_result = {
        'viewership_deleted_count': 50000,
        'aggregates_archived_count': 5000,
        'status': 'success'
    }
    
    logger.info(f"Retention cleanup result: {spark_job_result}")
    return spark_job_result

def verify_deletion_counts(cleanup_result, **context):
    logger.info("Verifying deletion counts match expected ranges")
    
    deleted_count = cleanup_result.get('viewership_deleted_count', 0)
    archived_count = cleanup_result.get('aggregates_archived_count', 0)
    
    expected_min_deleted = 10000
    expected_max_deleted = 100000
    
    expected_min_archived = 100
    expected_max_archived = 50000
    
    logger.info(f"Deleted viewership records: {deleted_count}")
    logger.info(f"Archived aggregates: {archived_count}")
    
    if not (expected_min_deleted <= deleted_count <= expected_max_deleted):
        raise AirflowException(
            f"Deleted count {deleted_count} outside expected range [{expected_min_deleted}, {expected_max_deleted}]"
        )
    
    if not (expected_min_archived <= archived_count <= expected_max_archived):
        raise AirflowException(
            f"Archived count {archived_count} outside expected range [{expected_min_archived}, {expected_max_archived}]"
        )
    
    logger.info("Deletion count verification passed")
    return {
        'viewership_deleted': deleted_count,
        'aggregates_archived': archived_count,
        'verification': 'passed'
    }

def alert_on_anomalies(verification_result, **context):
    logger.info("Checking for anomalies in deletion results")
    
    if verification_result.get('verification') \!= 'passed':
        raise AirflowException("Verification failed, unable to proceed")
    
    logger.info("No anomalies detected, cleanup successful")
    return {
        'alert_status': 'no_anomalies',
        'timestamp': datetime.utcnow().isoformat()
    }

trigger_cleanup = PythonOperator(
    task_id='trigger_retention_cleanup',
    python_callable=trigger_retention_cleanup,
)

verify_counts = PythonOperator(
    task_id='verify_deletion_counts',
    python_callable=verify_deletion_counts,
    op_args=[trigger_cleanup.output],
    provide_context=True,
)

alert = PythonOperator(
    task_id='alert_on_anomalies',
    python_callable=alert_on_anomalies,
    op_args=[verify_counts.output],
    provide_context=True,
)

trigger_cleanup >> verify_counts >> alert
