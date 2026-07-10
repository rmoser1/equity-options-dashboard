# Setup and Deployment

This document provides setup instructions for directory structure, Nginx
authentication, SSL certificates, Docker deployment, daily automation via
systemd, and operational debugging.

## Clone Repository and Prepare Folders

Deploy the project to a stable server path without spaces. The systemd templates
use this path:

```text
/opt/equity-options
```

Clone the repository and create bind-mount folders:

```bash
cd /opt
git clone https://github.com/rmoser1/equity-options-dashboard.git equity-options
cd equity-options
mkdir -p data/parquet logs/nginx nginx/certs
```

If you use a different deployment path, update both `WorkingDirectory` and
`ExecStart` in `deploy/systemd/equity-options-daily.service`.

## Create Nginx Basic Authentication

Create the basic-auth file required by the Nginx container:

```bash
htpasswd -c nginx/htpasswd user
```

You will be prompted to set a password for the user.

## Generate SSL Certificates

The Nginx proxy requires both `nginx/certs/fullchain.pem` and
`nginx/certs/privkey.pem` before it can start.

### Self-Signed Certificate for Local Testing

```bash
openssl req -x509 -newkey rsa:2048 \
  -keyout nginx/certs/privkey.pem \
  -out nginx/certs/fullchain.pem \
  -days 365 \
  -nodes \
  -subj "/CN=localhost"
```

### Production Certificate with Let's Encrypt

Generate certificates:

```bash
certbot certonly --standalone -d DOMAIN
```

Copy certificates into the project:

```bash
cp /etc/letsencrypt/live/DOMAIN/fullchain.pem nginx/certs/fullchain.pem
cp /etc/letsencrypt/live/DOMAIN/privkey.pem nginx/certs/privkey.pem
```

Replace `DOMAIN` with your actual domain name.

## Build and Run with Docker Compose

Ensure Docker and Docker Compose are installed.

```bash
docker compose build
docker compose up -d
```

The Compose stack is ordered so the batch jobs finish before the dashboard
starts:

```text
data_retrieval -> dashboard_data -> option_metrics -> app -> nginx
```

The `data_retrieval`, `dashboard_data`, and `option_metrics` services are
one-shot jobs. For a fresh stack startup, `app` and `nginx` start after all
batch jobs complete.

## Daily systemd Automation

The project includes a daily startup script and systemd unit templates:

- `scripts/daily-startup.sh`
- `deploy/systemd/equity-options-daily.service`
- `deploy/systemd/equity-options-daily.timer`

The script runs from the project root, rebuilds images, runs the batch jobs
while the existing dashboard stays online, then recreates `app` and `nginx` so
the dashboard loads the refreshed parquet files:

```bash
docker compose build data_retrieval dashboard_data option_metrics app nginx
docker compose run --rm --no-deps data_retrieval
docker compose run --rm --no-deps dashboard_data
docker compose run --rm --no-deps option_metrics
docker compose up -d --no-deps --force-recreate app
docker compose up -d --no-deps --force-recreate nginx
```

If either batch job fails, the script exits before recreating `app` or `nginx`,
leaving the previously running dashboard in place. After recreating `app`, the
script waits for its healthcheck before recreating `nginx`.

### Install the systemd Unit and Timer

Copy the systemd files into place:

```bash
sudo cp deploy/systemd/equity-options-daily.service /etc/systemd/system/
sudo cp deploy/systemd/equity-options-daily.timer /etc/systemd/system/
```

If your deployment path is not `/opt/equity-options`, edit the installed
service:

```bash
sudo nano /etc/systemd/system/equity-options-daily.service
```

Enable and start the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now equity-options-daily.timer
```

Schedule the daily job shortly after the U.S. equity market close at
4:00 p.m. Eastern time. The data retrieval step uses option ask quotes together
with underlying close prices; running during the trading session can mix live
option quotes with previous close prices, while running too late can hit Yahoo
option quotes that have been reset to zero before the next session. The options
pipeline detects that all-zero quote state on the first symbol and stops before
writing reset quotes to the database.

The timer is configured in server local time:

```ini
OnCalendar=*-*-* 20:00:00
```

Set `OnCalendar` to a local time that is safely after 4:00 p.m. Eastern time
for the server's timezone. Change the value in
`deploy/systemd/equity-options-daily.timer` before copying the file, or edit
`/etc/systemd/system/equity-options-daily.timer` after installation.

### Test the Daily Startup Manually

Run the script directly from the project:

```bash
scripts/daily-startup.sh
```

Or run the installed systemd service:

```bash
sudo systemctl start equity-options-daily.service
```

Check timer status and the next scheduled run:

```bash
systemctl status equity-options-daily.timer
systemctl list-timers equity-options-daily.timer
```

View the daily job logs:

```bash
journalctl -u equity-options-daily.service -n 100 --no-pager
```

## Monitoring and Debugging

View persistent project log files:

```bash
tail -f logs/data_retrieval.log
tail -f logs/dashboard_data.log
tail -f logs/option_metrics.log
tail -f logs/app.log
tail -f logs/app-access.log
tail -f logs/nginx/access.log
tail -f logs/nginx/error.log
```

View container stdout/stderr logs:

```bash
docker compose logs data_retrieval
docker compose logs dashboard_data
docker compose logs option_metrics
docker compose logs app
docker compose logs nginx
```

List running containers:

```bash
docker ps
```

Enter a running data-retrieval container:

```bash
docker exec -it equity-options-data_retrieval-1 /bin/bash
```
