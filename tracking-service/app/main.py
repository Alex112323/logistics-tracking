from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import broker, cache, db
from .auth import (
    TokenData,
    create_access_token,
    hash_password,
    require_role,
    verify_password,
)
import os

async def ensure_admin():
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_username or not admin_password:
        raise RuntimeError(
            "ADMIN_USERNAME and ADMIN_PASSWORD must be set in environment"
        )
    existing = await db.get_user_by_username(admin_username)
    if existing is None:
        await db.create_user(admin_username, hash_password(admin_password), "admin", is_active=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    await ensure_admin() 
    await cache.init_cache()
    await broker.init_broker()
    try:
        yield
    finally:
        await broker.close_broker()
        await cache.close_cache()
        await db.close_pool()


app = FastAPI(title="Tracking Service", lifespan=lifespan)
app.mount("/ui", StaticFiles(directory="app/static", html=True), name="static")


class ShipmentIn(BaseModel):
    status: Literal["created", "in_transit", "out_for_delivery", "delivered", "failed"]
    client_id: str | None = None


class UserIn(BaseModel):
    username: str
    password: str
    role: Literal["courier", "client"]


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/token")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = await db.get_user_by_username(form.username)
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad credentials")
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт курьера ожидает подтверждения администратором",
        )
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/shipments/{tracking_no}", status_code=202)
async def upsert(
    tracking_no: str,
    body: ShipmentIn,
    user: TokenData = Depends(require_role("courier")),
):
    row = await db.upsert_shipment(tracking_no, body.status, body.client_id)
    payload = {
        "tracking_no": row["tracking_no"],
        "status": row["status"],
        "client_id": row["client_id"],
        "updated_at": row["updated_at"],
    }
    await cache.set_status(tracking_no, payload)
    await broker.publish_status_changed({"event": "shipment.status_changed", **payload})
    return {"source": "db", **row}


@app.get("/shipments/{tracking_no}")
async def get(
    tracking_no: str,
    user: TokenData = Depends(require_role("client")),
):
    cached = await cache.get_status(tracking_no)
    if cached is not None:
        if cached.get("client_id") != user.username:
            raise HTTPException(403, "Not your shipment")
        return {"source": "cache", **cached}

    row = await db.fetch_shipment(tracking_no)
    if row is None:
        raise HTTPException(404, "shipment not found")
    if row["client_id"] != user.username:
        raise HTTPException(403, "Not your shipment")

    await cache.set_status(tracking_no, {
        "tracking_no": row["tracking_no"],
        "status": row["status"],
        "client_id": row["client_id"],
        "updated_at": row["updated_at"],
    })
    return {"source": "db", **row}


@app.delete("/shipments/{tracking_no}", status_code=202)
async def delete(
    tracking_no: str,
    user: TokenData = Depends(require_role("courier")),
):
    deleted = await db.delete_shipment(tracking_no)
    if not deleted:
        raise HTTPException(404, "shipment not found")
    await cache.get_cache().delete(cache.status_key(tracking_no))
    return {"deleted": True, "tracking_no": tracking_no}


@app.post("/users/register", status_code=201)
async def register(body: UserIn):
    hashed = hash_password(body.password)
    # курьер создаётся неактивным, клиент — активным
    is_active = (body.role == "client")
    user = await db.create_user(body.username, hashed, body.role, is_active=is_active)
    if user is None:
        raise HTTPException(409, "username already exists")
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "is_active": user["is_active"],
        "message": "Аккаунт создан" if is_active else "Аккаунт курьера ожидает подтверждения администратором",
    }
    
@app.post("/admin/approve/{username}")
async def approve(
    username: str,
    admin: TokenData = Depends(require_role("admin")),
):
    user = await db.approve_user(username)
    if user is None:
        raise HTTPException(404, "user not found")
    return {"approved": True, **user}