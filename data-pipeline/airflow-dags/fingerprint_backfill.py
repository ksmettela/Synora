from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {'owner': 'acraas', 'retries': 2, 'retry_delay': timedelta(minutes=5)}
dag = DAG('fingerprint_backfill', default_args=default_args, schedule_interval='@daily', start_date=datetime(2024, 1, 1))
def backfill_fingerprints(): return True
backfill_task = PythonOperator(task_id='backfill_fingerprints', python_callable=backfill_fingerprints, dag=dag)
