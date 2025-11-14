import os
import asyncio
import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Dict
import socket

CONTROLLER = os.getenv("CONTROLLER_ADDR", "http://controller:8000")
NODE_ID = os.getenv("NODE_ID", None)
PORT = int(os.getenv("PORT", "8001"))

app = FastAPI()
store: Dict[str, str] = {}

class KV(BaseModel):
    key: str
    value: str

async def register():
    async with httpx.AsyncClient() as client:
        host = socket.gethostname()
        req = {"node_id": NODE_ID or host, "host": host, "port": PORT}
        for _ in range(10):
            try:
                await client.post(f"{CONTROLLER}/register", json=req, timeout=5.0)
                return
            except Exception:
                await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(register())

@app.put("/kv")
async def put_kv(kv: KV):
    store[kv.key] = kv.value
    return {"status": "ok", "key": kv.key}

@app.get("/kv")
async def get_kv(key: str):
    if key in store:
        return {"found": True, "value": store[key]}
    raise HTTPException(status_code=404, detail="key not found")
