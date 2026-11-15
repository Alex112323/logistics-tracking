#!/bin/bash
set -e

echo "Waiting for master..."
until pg_isready -h tracking-db -p 5432 -U tracking; do
  sleep 2
done

echo "Running base backup from master..."
PGPASSWORD=replicator_pass pg_basebackup \
  -h tracking-db -p 5432 -U replicator \
  -D /var/lib/postgresql/data -Fp -Xs -R -P -v

echo "Base backup done, starting standby..."
exec docker-entrypoint.sh postgres