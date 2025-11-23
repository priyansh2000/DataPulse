from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Tuple
import time
import hashlib
import bisect
import asyncio
import httpx

app = FastAPI()

class RegisterReq(BaseModel):
    node_id: str
    host: str
    port: int

class HB(BaseModel):
    node_id: str

nodes: Dict[str, Dict] = {}
ring: List[Tuple[int, str]] = []
virtual_nodes = 3
timeout = 5

def hash_key(v: str) -> int:
    return int(hashlib.sha256(v.encode()).hexdigest(), 16)

def rebuild_ring():
    global ring
    ring = []
    for nid in nodes:
        for i in range(virtual_nodes):
            h = hash_key(f"{nid}-{i}")
            ring.append((h, nid))
    ring.sort(key=lambda x: x[0])

def get_replicas(key: str, count: int = 3) -> List[Dict]:
    active = [nid for nid, info in nodes.items() if info["status"] == "UP"]
    if not active:
        raise HTTPException(status_code=503, detail="no active nodes")
    active_set = set(active)
    filtered = [x for x in ring if x[1] in active_set]
    if not filtered:
        raise HTTPException(status_code=503, detail="no nodes")
    h = hash_key(key)
    hashes = [x[0] for x in filtered]
    idx = bisect.bisect_left(hashes, h)
    r = []
    used = set()
    i = idx
    while len(r) < min(count, len(active)):
        if i >= len(filtered):
            i = 0
        nid = filtered[i][1]
        if nid not in used:
            used.add(nid)
            info = nodes[nid]
            r.append({"node_id": nid, "host": info["host"], "port": info["port"]})
        i += 1
    return r

@app.post("/register")
async def register(req: RegisterReq):
    nodes[req.node_id] = {
        "host": req.host,
        "port": req.port,
        "ts": time.time(),
        "status": "UP"
    }
    rebuild_ring()
    return {"status": "registered"}

@app.post("/heartbeat")
async def heartbeat(hb: HB):
    if hb.node_id in nodes:
        nodes[hb.node_id]["ts"] = time.time()
        nodes[hb.node_id]["status"] = "UP"
    return {"status": "ok"}

@app.get("/nodes")
async def all_nodes():
    return {"nodes": nodes}

@app.get("/mapping")
async def mapping(key: str):
    return {"mapping": get_replicas(key)}

async def notify_failure(node_id: str):
    async with httpx.AsyncClient() as c:
        for nid, info in nodes.items():
            if nid == node_id:
                continue
            if info["status"] != "UP":
                continue
            url = f"http://{info['host']}:{info['port']}/node_down"
            data = {"node_id": node_id}
            try:
                await c.post(url, json=data, timeout=3)
            except:
                pass

async def check_failures():
    while True:
        now = time.time()
        failed = []
        for nid, info in nodes.items():
            if info["status"] == "UP" and now - info["ts"] > timeout:
                info["status"] = "DOWN"
                failed.append(nid)
        for f in failed:
            await notify_failure(f)
        await asyncio.sleep(1)

@app.on_event("startup")
async def start_monitor():
    asyncio.create_task(check_failures())
