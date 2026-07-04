FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV DASHBOARD_DATA_DIR=/app/data/parquet
ENV APP_LOG_FILE=/app/logs/app.log
ENV APP_ACCESS_LOG_FILE=/app/logs/app-access.log
ENV APP_ERROR_LOG_FILE=/app/logs/app.log

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-c", "gunicorn.conf.py", "dash_app:server"]
