#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

mkdir -p data/parquet logs/nginx nginx/certs

docker compose build data_retrieval dashboard_data option_metrics app nginx

docker compose run --rm --no-deps data_retrieval
docker compose run --rm --no-deps dashboard_data
docker compose run --rm --no-deps option_metrics

docker compose up -d --no-deps --force-recreate app

app_container_id="$(docker compose ps -q app)"
if [[ -z "${app_container_id}" ]]; then
    echo "app container was not created" >&2
    exit 1
fi

for _ in {1..60}; do
    app_health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${app_container_id}")"
    if [[ "${app_health}" == "healthy" || "${app_health}" == "none" ]]; then
        docker compose up -d --no-deps --force-recreate nginx
        exit 0
    fi

    if [[ "${app_health}" == "unhealthy" ]]; then
        echo "app container became unhealthy" >&2
        docker compose logs --tail=100 app >&2
        exit 1
    fi

    sleep 10
done

echo "app container did not become healthy within 10 minutes" >&2
docker compose logs --tail=100 app >&2
exit 1
