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
rebalancing = False

class KV(BaseModel):
    key: str
    value: str

class RepReq(BaseModel):
    key: str
    value: str

class NodeDownReq(BaseModel):
    node_id: str

def current_node_id() -> str:
    return NODE_ID or socket.gethostname()

async def register():
    async with httpx.AsyncClient() as c:
        nid = current_node_id()
        host = nid
        req = {"node_id": nid, "host": host, "port": PORT}
        for _ in range(30):
            try:
                await c.post(f"{CONTROLLER}/register", json=req, timeout=3)
                return
            except:
                await asyncio.sleep(1)

async def heartbeat():
    nid = current_node_id()
    data = {"node_id": nid}
    async with httpx.AsyncClient() as c:
        while True:
            try:
                await c.post(f"{CONTROLLER}/heartbeat", json=data, timeout=2)
            except:
                pass
            await asyncio.sleep(1)

@app.on_event("startup")
async def start():
    asyncio.create_task(register())
    asyncio.create_task(heartbeat())

async def fetch_mapping(key: str) -> List[Dict]:
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{CONTROLLER}/mapping", params={"key": key}, timeout=5)
        r.raise_for_status()
        return r.json()["mapping"]

async def replicate(node: Dict, kv: KV) -> bool:
    url = f"http://{node['host']}:{node['port']}/replicate"
    async with httpx.AsyncClient() as c:
        try:
            r = await c.post(url, json={"key": kv.key, "value": kv.value}, timeout=3)
            r.raise_for_status()
            return True
        except:
            return False

@app.put("/kv")
async def put(kv: KV):
    store[kv.key] = kv.value
    m = await fetch_mapping(kv.key)
    pid = m[0]["node_id"]
    nid = current_node_id()
    if pid != nid:
        return {"status": "ok", "role": "non_primary"}
    reps = m[1:]
    acks = 1
    if reps:
        if await replicate(reps[0], kv):
            acks += 1
    if len(reps) > 1:
        asyncio.create_task(replicate(reps[1], kv))
    if acks < 2:
        raise HTTPException(status_code=503, detail="quorum not reached")
    return {"status": "ok", "role": "primary", "replicas_acked": acks}

@app.post("/replicate")
async def r(req: RepReq):
    store[req.key] = req.value
    return {"status": "ok"}

async def rebalance_task():
    global rebalancing
    nid = current_node_id()
    items = list(store.items())
    for k, v in items:
        kv = KV(key=k, value=v)
        try:
            m = await fetch_mapping(k)
        except:
            continue
        for node in m:
            if node["node_id"] == nid:
                continue
            await replicate(node, kv)
    rebalancing = False

@app.post("/node_down")
async def node_down(req: NodeDownReq):
    global rebalancing
    if not rebalancing:
        rebalancing = True
        asyncio.create_task(rebalance_task())
    return {"status": "ok"}

@app.get("/kv")
async def get(key: str):
    if key in store:
        return {"found": True, "value": store[key]}
    raise HTTPException(status_code=404, detail="not found")

@app.get("/status")
async def status():
    return {"node_id": current_node_id(), "keys": len(store), "rebalancing": rebalancing}
