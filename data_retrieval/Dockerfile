FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data
ENV DATA_RETRIEVAL_LOG_FILE=/app/logs/data_retrieval.log

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
