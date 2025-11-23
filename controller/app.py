from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Tuple
import time
import hashlib
import bisect

app = FastAPI()

class RegisterReq(BaseModel):
    node_id: str
    host: str
    port: int

nodes: Dict[str, Dict] = {}
ring: List[Tuple[int, str]] = []
virtual_nodes = 3

def hash_key(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16)

def rebuild_ring():
    global ring
    ring = []
    for node_id, info in nodes.items():
        for i in range(virtual_nodes):
            h = hash_key(f"{node_id}-vn-{i}")
            ring.append((h, node_id))
    ring.sort(key=lambda x: x[0])

def get_replicas(key: str, count: int = 3) -> List[Dict]:
    if not ring:
        raise HTTPException(status_code=503, detail="no nodes available")
    h = hash_key(key)
    hashes = [x[0] for x in ring]
    idx = bisect.bisect_left(hashes, h)
    result_nodes = []
    seen = set()
    i = idx
    while len(result_nodes) < min(count, len(nodes)):
        if i >= len(ring):
            i = 0
        node_id = ring[i][1]
        if node_id not in seen:
            seen.add(node_id)
            info = nodes[node_id]
            if info["status"] == "UP":
                result_nodes.append(
                    {"node_id": node_id, "host": info["host"], "port": info["port"]}
                )
        i += 1
        if len(seen) == len(nodes):
            break
    if not result_nodes:
        raise HTTPException(status_code=503, detail="no active nodes")
    return result_nodes

@app.post("/register")
async def register(req: RegisterReq):
    nodes[req.node_id] = {
        "host": req.host,
        "port": req.port,
        "ts": time.time(),
        "status": "UP",
    }
    rebuild_ring()
    return {"status": "registered", "node_id": req.node_id}

@app.get("/nodes")
async def get_nodes():
    return {"nodes": nodes}

@app.get("/mapping")
async def mapping(key: str):
    mapping = get_replicas(key, 3)
    return {"mapping": mapping}
