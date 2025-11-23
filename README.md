

## **📌 Overview**

This project implements a **fault-tolerant, distributed key-value store** using:

* **Python + FastAPI**
* **Consistent Hashing**
* **Replication Factor = 3**
* **Write Quorum = 2**
* **Kubernetes (Minikube)**
* **Automatic Rebalancing on Node Failure**
* **Background Heartbeat Monitoring**

The system is composed of:

* **1 Controller Node**
* **4 Worker Nodes**

The controller manages mapping, membership, heartbeats, and failure detection.
Worker nodes store key-value pairs, replicate data, and rebalance on failures.

---

# **📌 Architecture**

```
                      ┌───────────────────┐
                      │    CONTROLLER     │
                      │  (FastAPI, K8s)   │
                      ├───────────────────┤
                      │ /register         │
                      │ /heartbeat        │
                      │ /mapping          │
                      │ /nodes            │
                      └───────────────────┘
                              ▲
                 Heartbeats   │
                              │
 ┌───────────────┬────────────┴───────────────┬────────────────┐
 │               │                              │               │
▼               ▼                              ▼               ▼
WORKER1       WORKER2                        WORKER3          WORKER4
(FastAPI)     (FastAPI)                      (FastAPI)        (FastAPI)
 └─────────── Replicas + Rebalancing + Quorum ─────────────────┘
```

---

# **📌 Key Features**

### ✔ **Consistent Hashing**

* Controller maintains a hash ring with virtual nodes.
* Keys map to a **primary** + **2 replicas**.

### ✔ **Replication (RF = 3)**

* Primary writes locally.
* Sync replicate to replica1.
* Async replicate to replica2.

### ✔ **Write Quorum**

* Minimum 2 acknowledgements required.

### ✔ **Automatic Heartbeats**

* Workers send `/heartbeat` every 1s.
* Controller marks nodes `UP` or `DOWN`.

### ✔ **Failure Detection + Rebalancing**

When a worker dies:

1. Controller detects timeout.
2. Controller marks it DOWN.
3. Controller notifies all active workers.
4. Workers rebalance their keys to new mapping.

### ✔ **Disaster Recovery**

Even if a worker disappears:

* System automatically restores replication factor.

---

# **📌 Microservices**

## **1️⃣ Controller**

* `/register`
* `/heartbeat`
* `/mapping`
* `/nodes`
* Failure detection loop
* Notifies workers on `/node_down`

## **2️⃣ Worker**

* `/kv` (PUT, GET)
* `/replicate`
* `/status`
* Rebalancing task
* Heartbeat sender
* Auto registration

---

# **📌 Directory Structure**

```
distributed-kv-python/
├── controller/
│   ├── app.py
│   └── Dockerfile
├── worker/
│   ├── app.py
│   └── Dockerfile
├── k8s/
│   ├── namespace.yaml
│   ├── controller-deployment.yaml
│   ├── controller-service.yaml
│   ├── worker1-deployment.yaml
│   ├── worker1-service.yaml
│   ├── worker2-deployment.yaml
│   ├── worker2-service.yaml
│   ├── worker3-deployment.yaml
│   ├── worker3-service.yaml
│   ├── worker4-deployment.yaml
│   └── worker4-service.yaml
├── docker-compose.yml
└── README.md
```

---

# **📌 Run Locally using Docker Compose**

```
docker-compose up --build
```

Controller:

```
curl http://localhost:8000/nodes
curl "http://localhost:8000/mapping?key=user123"
```

Workers:

* worker1 → 8101
* worker2 → 8201
* worker3 → 8301
* worker4 → 8401

---

# **📌 Deploy on Kubernetes (Minikube)**

## **1. Start Minikube**

```
minikube start --driver=docker
eval $(minikube docker-env)
```

## **2. Build Images inside Minikube**

```
docker build -t distributed-kv-controller:latest ./controller
docker build -t distributed-kv-worker:latest ./worker
```

## **3. Apply Kubernetes Files**

```
kubectl apply -f k8s/
kubectl get pods -n kv-system
```

---

# **📌 Demo: Key Mapping + Replication**

### 1. Get mapping

```
curl "http://localhost:8000/mapping?key=user123"
```

### 2. Write to primary

Example (primary = worker3):

```
curl -X PUT "http://localhost:8301/kv" \
 -H "Content-Type: application/json" \
 -d '{"key":"user123","value":"hello"}'
```

### 3. Check replicas

```
curl http://localhost:8201/kv?key=user123
curl http://localhost:8101/kv?key=user123
curl http://localhost:8401/kv?key=user123
```

---

# **📌 Demo: Failure Handling + Rebalancing**

### 1. Scale down worker3

```
kubectl scale deployment worker3 -n kv-system --replicas=0
```

### 2. Controller marks DOWN

```
curl http://localhost:8000/nodes
```

### 3. Check key exists on new mapping nodes

```
curl "http://localhost:8000/mapping?key=user123"
```

Now worker3 will not appear.

Check:

```
curl http://localhost:8101/kv?key=user123
curl http://localhost:8201/kv?key=user123
curl http://localhost:8401/kv?key=user123
```

---

# **📌 Evaluation Points to Mention During Viva**

* Why consistent hashing avoids large remapping
* Why replication factor = 3
* Why quorum=2 (availability over consistency)
* How controller maintains membership
* How heartbeats detect failures
* Why rebalancing is needed
* Why Kubernetes Deployments restart pods by default
* How failure simulation works using scaling
* Why Minikube was used (local production-like environment)

---

# **📌 Git Commit for This Stage**

```
git add README.md DEMO.md
git commit -m "docs: add complete README and demo instructions for distributed KV system"
```

---


