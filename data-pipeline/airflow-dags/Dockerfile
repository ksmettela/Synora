FROM apache/airflow:2.8.0-python3.11

USER root

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY plugins/ ${AIRFLOW_HOME}/plugins/
COPY dags/ ${AIRFLOW_HOME}/dags/

ENV AIRFLOW__CORE__DAGS_FOLDER=${AIRFLOW_HOME}/dags
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG=3
ENV AIRFLOW__SCHEDULER__CATCHUP_BY_DEFAULT=False

EXPOSE 8080
