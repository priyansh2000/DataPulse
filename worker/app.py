import os
import asyncio
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import socket

CONTROLLER = os.getenv("CONTROLLER_ADDR", "http://controller:8000")
NODE_ID = os.getenv("NODE_ID", None)
PORT = int(os.getenv("PORT", "8001"))

app = FastAPI()
store: Dict[str, str] = {}

class KV(BaseModel):
    key: str
    value: str

class ReplicateReq(BaseModel):
    key: str
    value: str

async def register():
    async with httpx.AsyncClient() as client:
        host = socket.gethostname()
        nid = NODE_ID or host
        req = {"node_id": nid, "host": host, "port": PORT}
        for _ in range(30):
            try:
                await client.post(f"{CONTROLLER}/register", json=req, timeout=5.0)
                return
            except Exception:
                await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(register())

async def fetch_mapping(key: str) -> List[Dict]:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{CONTROLLER}/mapping", params={"key": key}, timeout=5.0)
        r.raise_for_status()
        data = r.json()
        return data["mapping"]

async def replicate_to_node(node: Dict, kv: KV) -> bool:
    url = f"http://{node['host']}:{node['port']}/replicate"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json={"key": kv.key, "value": kv.value}, timeout=3.0)
            r.raise_for_status()
            return True
        except Exception:
            return False

@app.put("/kv")
async def put_kv(kv: KV):
    store[kv.key] = kv.value
    mapping = await fetch_mapping(kv.key)
    primary = mapping[0]
    if primary["node_id"] != (NODE_ID or socket.gethostname()):
        return {"status": "ok", "key": kv.key, "role": "non_primary", "replicas_acked": 1}
    replicas = mapping[1:]
    acks = 1
    if replicas:
        first = replicas[0]
        ok = await replicate_to_node(first, kv)
        if ok:
            acks += 1
    if len(replicas) > 1:
        second = replicas[1]
        asyncio.create_task(replicate_to_node(second, kv))
    if acks < 2 and len(replicas) > 0:
        raise HTTPException(status_code=503, detail="quorum not reached")
    return {"status": "ok", "key": kv.key, "role": "primary", "replicas_acked": acks}

@app.post("/replicate")
async def replicate(req: ReplicateReq):
    store[req.key] = req.value
    return {"status": "ok", "key": req.key}

@app.get("/kv")
async def get_kv(key: str):
    if key in store:
        return {"found": True, "value": store[key]}
    raise HTTPException(status_code=404, detail="key not found")

@app.get("/status")
async def status():
    return {"node_id": NODE_ID or socket.gethostname(), "keys": len(store)}
