## Параметры обслуживания (SLO, MTBF, MTTR)

### Целевой уровень доступности (SLO)

**SLO: 99.9%**  — не более **43 минут недоступности в месяц**.

Обоснование: кластер спроектирован с автоматическим failover (Patroni + HAProxy + RabbitMQ quorum queues), что даёт MTTR в пределах 1 минуты при одиночном
отказе ноды. SLO 99.9% оставляет запас на плановое обслуживание и ручные
действия при сложных сбоях. 99.99% (4 минуты в месяц) было бы нереалистично
для проекта без круглосуточного дежурства.

### MTBF (Mean Time Between Failures)

**MTBF: 180 часов (7 дней)** — один сбой в неделю.

Обоснование: одиночный отказ ноды (Patroni, RabbitMQ, etcd) не приводит к
сбою сервиса — failover автоматический. Сбоем считается ситуация, когда
сервис недоступен для клиента (все ноды Postgres или RabbitMQ недоступны,
или сеть между компонентами нарушена). Для учебного проекта заложен один
такой сбой в месяц.

### MTTR (Mean Time To Repair)

**MTTR: 5 минут**.

Обоснование:
- Patroni выбирает нового лидера за `ttl + loop_wait` = 30 + 10 = **40 секунд**.
- HAProxy переключает трафик за **3–5 секунд** (интервал healthcheck).
- RabbitMQ Raft выбирает нового лидера очереди за **5–10 секунд**.
- Автоматическое восстановление — **до 1 минуты**.
- MTTR 5 минут включает обнаружение алерта, проверку `patronictl list` и
  подтверждение, что failover прошёл. Ручное вмешательство требуется только
  при отказе большинства нод (кворум потерян).

### Расчёт доступности

Availability = MTBF / (MTBF + MTTR) = 180 / (180 + 5/60) ≈ 99.95%

Заявленный SLO 99.9% ниже расчётного — это осознанный запас на плановое
обслуживание и сложные сбои.

### Команды
#### Регистрация и логин
```bash
curl -X POST localhost:8000/users/register -H 'Content-Type: application/json' -d '{"username":"alice","password":"pass123","role":"client"}'
curl -X POST localhost:8000/users/register -H 'Content-Type: application/json' -d '{"username":"courier1","password":"pass123","role":"courier"}'

ADMIN_TOKEN=$(curl -s -X POST localhost:8000/token -d 'username=admin&password=admin123' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -X POST localhost:8000/admin/approve/courier1 -H "Authorization: Bearer $ADMIN_TOKEN"

COURIER_TOKEN=$(curl -s -X POST localhost:8000/token -d 'username=courier1&password=pass123' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```
#### Запись в БД + outbox
```bash
curl -X POST localhost:8000/shipments/TRK1 -H "Authorization: Bearer $COURIER_TOKEN" -H 'Content-Type: application/json' -d '{"status":"created","client_id":"alice"}'
docker compose exec patroni1 psql -U postgres -d logistics -c "SELECT id, event_type, published FROM outbox ORDER BY id DESC LIMIT 1;"
```
#### Publish/consume через Outbox
```bash
docker compose logs outbox-dispatcher | tail -3
docker compose logs event-worker | tail -3
```

#### отказоустойчивая СУБД (Patroni)
```bash
docker compose exec patroni1 patronictl -c /etc/patroni/patroni.yml list
docker compose stop patroni1
sleep 35
docker compose exec patroni2 patronictl -c /etc/patroni/patroni.yml list
curl -X POST localhost:8000/shipments/TRK2 -H "Authorization: Bearer $COURIER_TOKEN" -H 'Content-Type: application/json' -d '{"status":"in_transit","client_id":"alice"}'
docker compose start patroni1
sleep 20
docker compose exec patroni2 patronictl -c /etc/patroni/patroni.yml list
```
#### отказоустойчивый брокер (RabbitMQ)
```bash
docker compose exec rabbitmq2 rabbitmqctl cluster_status
docker compose exec rabbitmq2 rabbitmq-queues quorum_status events.raw
docker compose stop rabbitmq3
sleep 10
docker compose exec rabbitmq1 rabbitmq-queues quorum_status events.raw
curl -X POST localhost:8000/shipments/TRK3 -H "Authorization: Bearer $COURIER_TOKEN" -H 'Content-Type: application/json' -d '{"status":"created","client_id":"alice"}'
docker compose logs event-worker | tail -3
docker compose start rabbitmq3
```