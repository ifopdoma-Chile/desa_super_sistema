#!/bin/bash
cd /Data2/super_sistema
export HDO_CONFIG=production
export HDO_DB_HOST=localhost
export HDO_DB_PORT=5432
export HDO_DB_NAME=hdo
export HDO_DB_USER=postgres
export HDO_DB_PASS=hdo2026
export CMEMS_USERNAME=agarcia5
export CMEMS_PASSWORD=Dream.2004
exec /usr/bin/gunicorn --workers 5 --worker-class sync --bind 0.0.0.0:8084 --timeout 120 wsgi:app
