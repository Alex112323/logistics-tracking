-- db/init.sql
CREATE TABLE IF NOT EXISTS shipments (
    tracking_no TEXT PRIMARY KEY, 
    status      TEXT NOT NULL DEFAULT 'created'
                CHECK (status IN ('created','in_transit','out_for_delivery','delivered','failed')),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);