#!/bin/bash
set -e

CONNSTRING="$1"
echo "Applying schema to $CONNSTRING"

# 1. Создать базу (conninfo через -d)
psql -d "$CONNSTRING" -c "CREATE DATABASE logistics;" 2>/dev/null || echo "Database logistics already exists"

# 2. Применить схему к logistics (conninfo через -d, база через -d? нет — через переменную)
# Вариант: передать conninfo через -d, а базу через PGDATABASE
psql -d "$CONNSTRING dbname=logistics" -f /init.sql

echo "Schema applied successfully"