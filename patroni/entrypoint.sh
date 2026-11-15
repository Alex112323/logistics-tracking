#!/bin/bash
set -e

# Если data directory существует и принадлежит root — исправляем права
if [ -d /var/lib/postgresql/data ]; then
    chown -R postgres:postgres /var/lib/postgresql/data
    chmod 700 /var/lib/postgresql/data
fi

# Переключаемся на postgres и запускаем patroni
exec gosu postgres patroni /etc/patroni/patroni.yml