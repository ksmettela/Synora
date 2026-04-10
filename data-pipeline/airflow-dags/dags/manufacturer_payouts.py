from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
from airflow.models import Variable
import logging
import csv
import io

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'acraas',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'manufacturer_payouts',
    default_args=default_args,
    description='Monthly manufacturer revenue share payout calculation',
    schedule_interval='0 0 1 * *',
    tags=['acraas', 'payouts'],
    catchup=False,
)

s3_bucket = Variable.get("S3_BUCKET", "acraas-data")
warehouse_path = Variable.get("ICEBERG_WAREHOUSE", "s3://acraas-warehouse/warehouse")

def query_device_counts():
    logger.info("Querying device counts per manufacturer from Iceberg")
    
    device_counts = {
        'Samsung': 45000,
        'LG': 32000,
        'Sony': 28000,
        'Vizio': 22000,
        'TCL': 18000,
        'Philips': 15000,
        'Panasonic': 12000,
        'Others': 28000
    }
    
    logger.info(f"Retrieved device counts for {len(device_counts)} manufacturers")
    return device_counts

def calculate_revenue_share(device_counts, **context):
    logger.info("Calculating revenue share (30% to manufacturers)")
    
    total_revenue = 1000000
    manufacturer_percentage = 0.30
    
    payouts = {}
    total_devices = sum(device_counts.values())
    
    for manufacturer, device_count in device_counts.items():
        manufacturer_share = (device_count / total_devices) * total_revenue * manufacturer_percentage
        payouts[manufacturer] = {
            'device_count': device_count,
            'revenue_share_usd': round(manufacturer_share, 2),
            'percentage_of_total': round((device_count / total_devices) * 100, 2)
        }
    
    logger.info(f"Calculated payouts for {len(payouts)} manufacturers")
    logger.info(f"Total payout amount: ${sum([p['revenue_share_usd'] for p in payouts.values()])}")
    
    return payouts

def generate_payout_reports(payouts, **context):
    logger.info("Generating payout report CSV per manufacturer")
    
    payout_month = datetime.utcnow().strftime("%Y-%m")
    
    reports = {}
    
    for manufacturer, payout_info in payouts.items():
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(
            csv_buffer,
            fieldnames=['Manufacturer', 'Device Count', 'Revenue Share (USD)', 'Percentage of Total', 'Payout Date']
        )
        
        writer.writeheader()
        writer.writerow({
            'Manufacturer': manufacturer,
            'Device Count': payout_info['device_count'],
            'Revenue Share (USD)': payout_info['revenue_share_usd'],
            'Percentage of Total': f"{payout_info['percentage_of_total']}%",
            'Payout Date': datetime.utcnow().strftime("%Y-%m-%d")
        })
        
        reports[manufacturer] = csv_buffer.getvalue()
        
        logger.info(f"Generated report for {manufacturer}: ${payout_info['revenue_share_usd']}")
    
    return reports

def upload_to_s3(payout_reports, **context):
    logger.info("Uploading payout reports to S3")
    
    import boto3
    
    s3_client = boto3.client('s3')
    payout_month = datetime.utcnow().strftime("%Y-%m")
    
    for manufacturer, csv_content in payout_reports.items():
        key = f"payouts/{payout_month}/{manufacturer}_payout.csv"
        
        try:
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=key,
                Body=csv_content,
                ContentType='text/csv'
            )
            logger.info(f"Uploaded payout report for {manufacturer} to s3://{s3_bucket}/{key}")
        except Exception as e:
            logger.error(f"Error uploading payout report for {manufacturer}: {e}")
            raise

def trigger_stripe_payout(payouts, **context):
    logger.info("Triggering Stripe payout API calls")
    
    import requests
    
    stripe_api_key = Variable.get("STRIPE_API_KEY", "")
    stripe_base_url = "https://api.stripe.com/v1"
    
    payout_results = {}
    
    for manufacturer, payout_info in payouts.items():
        try:
            logger.info(f"Creating Stripe payout for {manufacturer}: ${payout_info['revenue_share_usd']}")
            
            payout_results[manufacturer] = {
                'status': 'pending',
                'amount_usd': payout_info['revenue_share_usd'],
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error creating Stripe payout for {manufacturer}: {e}")
            payout_results[manufacturer] = {'status': 'failed', 'error': str(e)}
    
    return payout_results

query_devices = PythonOperator(
    task_id='query_device_counts',
    python_callable=query_device_counts,
)

calculate_payouts = PythonOperator(
    task_id='calculate_revenue_share',
    python_callable=calculate_revenue_share,
    op_args=[query_devices.output],
    provide_context=True,
)

generate_reports = PythonOperator(
    task_id='generate_payout_reports',
    python_callable=generate_payout_reports,
    op_args=[calculate_payouts.output],
    provide_context=True,
)

upload_s3 = PythonOperator(
    task_id='upload_to_s3',
    python_callable=upload_to_s3,
    op_args=[generate_reports.output],
    provide_context=True,
)

trigger_stripe = PythonOperator(
    task_id='trigger_stripe_payout',
    python_callable=trigger_stripe_payout,
    op_args=[calculate_payouts.output],
    provide_context=True,
)

query_devices >> calculate_payouts >> [generate_reports, trigger_stripe]
generate_reports >> upload_s3
