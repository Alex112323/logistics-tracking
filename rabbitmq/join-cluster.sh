#!/bin/bash
set -e

# 1. Запускаем стандартный entrypoint в фоне (он запустит rabbitmq-server)
/usr/local/bin/docker-entrypoint.sh rabbitmq-server &
ENTRYPOINT_PID=$!

# 2. Ждём, пока сервер RabbitMQ будет готов
echo "Waiting for RabbitMQ to start..."
until rabbitmq-diagnostics -q ping >/dev/null 2>&1; do
  sleep 2
done
echo "RabbitMQ is up."

# 3. Если это не сид-нода, присоединяемся к кластеру
if [ "$(hostname)" != "rabbitmq1" ]; then
  echo "Joining cluster via rabbitmq1..."
  rabbitmqctl stop_app
  rabbitmqctl reset
  rabbitmqctl join_cluster rabbit@rabbitmq1
  rabbitmqctl start_app
fi

# 4. Ждём завершения фонового процесса (чтобы контейнер не завершился)
wait $ENTRYPOINT_PID