CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('admin', 'courier', 'client')),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS shipments (
    tracking_no TEXT PRIMARY KEY,
    status      TEXT NOT NULL DEFAULT 'created'
                CHECK (status IN ('created','in_transit','out_for_delivery','delivered','failed')),
    client_id   TEXT REFERENCES users(username),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);