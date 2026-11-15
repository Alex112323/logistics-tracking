FROM postgres:16-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev libpq-dev curl gosu \
    python3-etcd \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    patroni \
    psycopg2-binary

RUN mkdir -p /etc/patroni /var/lib/postgresql/data \
    && chown -R postgres:postgres /etc/patroni /var/lib/postgresql/data

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]