from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import time

app = FastAPI()
nodes: Dict[str, Dict] = {}

class RegisterReq(BaseModel):
    node_id: str
    host: str
    port: int

@app.post("/register")
async def register(req: RegisterReq):
    nodes[req.node_id] = {"host": req.host, "port": req.port, "ts": time.time(), "status": "UP"}
    return {"status": "registered", "node_id": req.node_id}

@app.get("/nodes")
async def get_nodes():
    return {"nodes": nodes}

@app.get("/mapping")
async def mapping(key: str):
    if not nodes:
        raise HTTPException(status_code=503, detail="no nodes available")
    node_list = list(nodes.items())
    addrs = []
    for i in range(3):
        idx = (hash(key) + i) % len(node_list)
        nid, info = node_list[idx]
        addrs.append({"node_id": nid, "host": info["host"], "port": info["port"]})
    return {"mapping": addrs}
