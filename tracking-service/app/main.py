from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import broker, cache, db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    await cache.init_cache()
    await broker.init_broker()
    try:
        yield
    finally:
        await broker.close_broker()
        await cache.close_cache()
        await db.close_pool()


app = FastAPI(title="Tracking Service", lifespan=lifespan)


class ShipmentIn(BaseModel):
    status: Literal["created", "in_transit", "out_for_delivery", "delivered", "failed"]


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/shipments/{tracking_no}")
async def upsert(tracking_no: str, body: ShipmentIn):
    # 1) запись в БД (upsert)
    row = await db.upsert_shipment(tracking_no, body.status)

    # 2) обновление кэша
    payload = {
        "tracking_no": row["tracking_no"],
        "status": row["status"],
        "updated_at": row["updated_at"],
    }
    await cache.set_status(tracking_no, payload)

    # 3) публикация события в брокер
    await broker.publish_status_changed({
        "event": "shipment.status_changed",
        **payload,
    })

    return {"source": "db", **row}


@app.get("/shipments/{tracking_no}")
async def get(tracking_no: str):
    cached = await cache.get_status(tracking_no)
    if cached is not None:
        return {"source": "cache", **cached}

    row = await db.fetch_shipment(tracking_no)
    if row is None:
        raise HTTPException(status_code=404, detail="shipment not found")

    await cache.set_status(tracking_no, {
        "tracking_no": row["tracking_no"],
        "status": row["status"],
        "updated_at": row["updated_at"],
    })
    return {"source": "db", **row}

@app.delete("/shipments/{tracking_no}")
async def delete(tracking_no: str):
    deleted = await db.delete_shipment(tracking_no)
    if not deleted:
        raise HTTPException(status_code=404, detail="shipment not found")

    # инвалидация кэша — данные удалены, кэш больше не актуален
    await cache.get_cache().delete(cache.status_key(tracking_no))

    return {"deleted": True, "tracking_no": tracking_no}