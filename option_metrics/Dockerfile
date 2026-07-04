FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV DASHBOARD_DATA_DIR=/app/data/parquet
ENV OPTION_METRICS_LOG_FILE=/app/logs/option_metrics.log

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . ./option_metrics

CMD ["python", "-m", "option_metrics.main"]
