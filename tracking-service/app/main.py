from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    try:
        yield
    finally:
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
    row = await db.fetch_shipment(tracking_no)
    if row is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    return {"source": "db", **row}