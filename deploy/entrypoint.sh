#!/bin/sh
set -e

cd /opt/vue-fastapi-admin

mkdir -p storage/knowledge storage/exam/banks app/logs

nginx
exec uvicorn app:app --host 0.0.0.0 --port 9999
