FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV FAUST_WORKDIR=/app

EXPOSE 6066

CMD ["python", "-m", "faust", "-A", "app", "worker", "-l", "info"]
