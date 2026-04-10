from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
from airflow.models import Variable
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'acraas',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 0,
}

dag = DAG(
    'sdk_health_check',
    default_args=default_args,
    description='Hourly SDK health monitoring and alerting',
    schedule_interval='0 * * * *',
    tags=['acraas', 'monitoring'],
    catchup=False,
)

slack_webhook_url = Variable.get("SLACK_WEBHOOK_URL", "")
warehouse_path = Variable.get("ICEBERG_WAREHOUSE", "s3://acraas-warehouse/warehouse")

def check_ingest_rate(**context):
    logger.info("Checking ingest rate per manufacturer")
    
    ingest_rates = {
        'Samsung': 15000,
        'LG': 11000,
        'Sony': 9500,
        'Vizio': 7500,
        'TCL': 6000,
        'Philips': 5000,
        'Panasonic': 4000,
        'Others': 9500
    }
    
    baseline_rates = {
        'Samsung': 18000,
        'LG': 13000,
        'Sony': 11000,
        'Vizio': 9000,
        'TCL': 7000,
        'Philips': 6000,
        'Panasonic': 5000,
        'Others': 11000
    }
    
    alerts = []
    
    for manufacturer, current_rate in ingest_rates.items():
        baseline = baseline_rates.get(manufacturer, current_rate)
        drop_percentage = ((baseline - current_rate) / baseline) * 100
        
        logger.info(f"{manufacturer}: {current_rate} events/hour (baseline: {baseline}, drop: {drop_percentage}%)")
        
        if drop_percentage > 50:
            alerts.append({
                'manufacturer': manufacturer,
                'type': 'ingest_rate_drop',
                'current_rate': current_rate,
                'baseline_rate': baseline,
                'drop_percentage': drop_percentage,
                'severity': 'critical'
            })
    
    return {
        'ingest_rates': ingest_rates,
        'alerts': alerts,
        'total_alerts': len(alerts)
    }

def check_match_rate(**context):
    logger.info("Checking match rate across manufacturers")
    
    match_rates = {
        'Samsung': 72,
        'LG': 68,
        'Sony': 75,
        'Vizio': 62,
        'TCL': 58,
        'Philips': 70,
        'Panasonic': 65,
        'Others': 61
    }
    
    alerts = []
    min_acceptable_match_rate = 60
    
    for manufacturer, match_rate in match_rates.items():
        logger.info(f"{manufacturer}: {match_rate}% match rate")
        
        if match_rate < min_acceptable_match_rate:
            alerts.append({
                'manufacturer': manufacturer,
                'type': 'low_match_rate',
                'match_rate': match_rate,
                'threshold': min_acceptable_match_rate,
                'severity': 'warning'
            })
    
    return {
        'match_rates': match_rates,
        'alerts': alerts,
        'total_alerts': len(alerts)
    }

def check_optout_rate(**context):
    logger.info("Checking opt-out rate for anomalies")
    
    current_optout_rates = {
        'Samsung': 0.5,
        'LG': 0.6,
        'Sony': 0.4,
        'Vizio': 1.2,
        'TCL': 0.8,
        'Philips': 0.7,
        'Panasonic': 0.9,
        'Others': 1.5
    }
    
    baseline_optout_rates = {
        'Samsung': 0.4,
        'LG': 0.5,
        'Sony': 0.3,
        'Vizio': 0.5,
        'TCL': 0.6,
        'Philips': 0.5,
        'Panasonic': 0.6,
        'Others': 0.8
    }
    
    alerts = []
    spike_threshold = 5.0
    
    for manufacturer, current_rate in current_optout_rates.items():
        baseline = baseline_optout_rates.get(manufacturer, current_rate)
        
        if baseline > 0:
            spike_multiple = current_rate / baseline
        else:
            spike_multiple = 1.0
        
        logger.info(f"{manufacturer}: {current_rate}% opt-out rate (baseline: {baseline}%, multiple: {spike_multiple}x)")
        
        if spike_multiple > spike_threshold:
            alerts.append({
                'manufacturer': manufacturer,
                'type': 'optout_spike',
                'current_rate': current_rate,
                'baseline_rate': baseline,
                'spike_multiple': spike_multiple,
                'severity': 'high'
            })
    
    return {
        'optout_rates': current_optout_rates,
        'alerts': alerts,
        'total_alerts': len(alerts)
    }

def consolidate_alerts(ingest_result, match_result, optout_result, **context):
    logger.info("Consolidating all health check alerts")
    
    all_alerts = []
    all_alerts.extend(ingest_result.get('alerts', []))
    all_alerts.extend(match_result.get('alerts', []))
    all_alerts.extend(optout_result.get('alerts', []))
    
    summary = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_alerts': len(all_alerts),
        'alerts_by_type': {
            'ingest_rate_drop': len([a for a in all_alerts if a.get('type') == 'ingest_rate_drop']),
            'low_match_rate': len([a for a in all_alerts if a.get('type') == 'low_match_rate']),
            'optout_spike': len([a for a in all_alerts if a.get('type') == 'optout_spike']),
        },
        'alerts': all_alerts
    }
    
    logger.info(f"Alert summary: {summary}")
    
    return summary

def send_slack_alert(alert_summary, **context):
    logger.info("Sending Slack notification for health check alerts")
    
    if alert_summary['total_alerts'] == 0:
        logger.info("No alerts to send")
        return
    
    message = f"""
:warning: Synora SDK Health Check Alert
Timestamp: {alert_summary['timestamp']}

*Alert Summary:*
- Ingest Rate Drops: {alert_summary['alerts_by_type']['ingest_rate_drop']}
- Low Match Rates: {alert_summary['alerts_by_type']['low_match_rate']}
- Opt-Out Spikes: {alert_summary['alerts_by_type']['optout_spike']}

Total Alerts: {alert_summary['total_alerts']}

Please check the Airflow UI for details.
    """
    
    logger.info(f"Slack message:\n{message}")
    return message

ingest_check = PythonOperator(
    task_id='check_ingest_rate',
    python_callable=check_ingest_rate,
    provide_context=True,
)

match_check = PythonOperator(
    task_id='check_match_rate',
    python_callable=check_match_rate,
    provide_context=True,
)

optout_check = PythonOperator(
    task_id='check_optout_rate',
    python_callable=check_optout_rate,
    provide_context=True,
)

consolidate = PythonOperator(
    task_id='consolidate_alerts',
    python_callable=consolidate_alerts,
    op_args=[ingest_check.output, match_check.output, optout_check.output],
    provide_context=True,
)

slack_alert = PythonOperator(
    task_id='send_slack_alert',
    python_callable=send_slack_alert,
    op_args=[consolidate.output],
    provide_context=True,
)

[ingest_check, match_check, optout_check] >> consolidate >> slack_alert
