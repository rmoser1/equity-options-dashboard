"""Gunicorn configuration for the dashboard container."""

import os
from pathlib import Path


bind = "0.0.0.0:8050"
capture_output = True
loglevel = os.getenv("LOG_LEVEL", "info").lower()

accesslog = os.getenv("APP_ACCESS_LOG_FILE", "/app/logs/app-access.log")
errorlog = (
    os.getenv("APP_ERROR_LOG_FILE")
    or os.getenv("LOG_FILE")
    or "/app/logs/app.log"
)

for log_file in (accesslog, errorlog):
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
