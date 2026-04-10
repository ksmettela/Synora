from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'acraas',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'daily_reporting',
    default_args=default_args,
    description='Generate daily reports',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
)

def generate_reports():
    print("Generating daily reports...")
    return True

report_task = PythonOperator(
    task_id='generate_reports',
    python_callable=generate_reports,
    dag=dag,
)
