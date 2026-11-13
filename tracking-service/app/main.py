from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import cache, db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    await cache.init_cache()
    try:
        yield
    finally:
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
    row = await db.upsert_shipment(tracking_no, body.status)
    return {"source": "db", **row}


@app.get("/shipments/{tracking_no}")
async def get(tracking_no: str):
    # 1) сначала кэш
    cached = await cache.get_status(tracking_no)
    if cached is not None:
        return {"source": "cache", **cached}

    # 2) промах кэша — идём в БД
    row = await db.fetch_shipment(tracking_no)
    if row is None:
        raise HTTPException(status_code=404, detail="shipment not found")

    # 3) прогреваем кэш
    await cache.set_status(tracking_no, {
        "tracking_no": row["tracking_no"],
        "status": row["status"],
        "updated_at": row["updated_at"],
    })
    return {"source": "db", **row}