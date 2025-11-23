

### Step 0 – Setup (before going to lab/presentation)

On your laptop:

```bash
minikube start --driver=docker
eval $(minikube docker-env)

cd ~/Desktop/heartbeat

docker build -t distributed-kv-controller:latest ./controller
docker build -t distributed-kv-worker:latest ./worker

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/controller-deployment.yaml
kubectl apply -f k8s/controller-service.yaml
kubectl apply -f k8s/worker1-deployment.yaml
kubectl apply -f k8s/worker1-service.yaml
kubectl apply -f k8s/worker2-deployment.yaml
kubectl apply -f k8s/worker2-service.yaml
kubectl apply -f k8s/worker3-deployment.yaml
kubectl apply -f k8s/worker3-service.yaml
kubectl apply -f k8s/worker4-deployment.yaml
kubectl apply -f k8s/worker4-service.yaml

kubectl get pods -n kv-system
```

Say:

> “Here I have deployed one controller and four worker nodes as Kubernetes pods inside Minikube.”

You should see 5 pods all `Running`.

---

### Step 1 – Show controller view of cluster

Port-forward controller:

```bash
kubectl port-forward svc/controller -n kv-system 8000:8000
```

In another terminal:

```bash
curl http://localhost:8000/nodes
```

Say:

> “The controller tracks all workers, their host, port, last heartbeat timestamp, and status (UP/DOWN).”

---

### Step 2 – Show mapping for a key using consistent hashing

```bash
curl "http://localhost:8000/mapping?key=user123"
```

Explain:

> “For key = user123, the controller uses consistent hashing to select a primary and two replica workers. This mapping is stable as long as the worker set doesn’t change.”

Note which workers appear and which one is first → that’s the **primary**.

---

### Step 3 – Port-forward workers and test replication

In separate terminals:

```bash
kubectl port-forward svc/worker1 -n kv-system 8101:8001
kubectl port-forward svc/worker2 -n kv-system 8201:8001
kubectl port-forward svc/worker3 -n kv-system 8301:8001
kubectl port-forward svc/worker4 -n kv-system 8401:8001
```

Now, based on mapping, pick the **primary** for `user123`.
Example: if primary in mapping is `worker3`:

```bash
curl -X PUT "http://localhost:8301/kv" \
  -H "Content-Type: application/json" \
  -d '{"key":"user123","value":"hello-k8s"}'
```

Then check each mapped worker:

```bash
curl "http://localhost:8301/kv?key=user123"
curl "http://localhost:8201/kv?key=user123"
curl "http://localhost:8101/kv?key=user123"
curl "http://localhost:8401/kv?key=user123"
```

Explain:

> “The write goes to the primary. It synchronously replicates to one replica (write quorum of 2) and asynchronously to the third replica. That’s why the value appears immediately on at least two nodes.”

---

### Step 4 – Failure + rebalancing demo (important)

Now show fault tolerance.

1. First, show current nodes:

```bash
curl http://localhost:8000/nodes
```

2. Scale down worker3 to **simulate permanent node failure**:

```bash
kubectl scale deployment worker3 -n kv-system --replicas=0
```

Wait ~8 seconds.

3. Check nodes again:

```bash
curl http://localhost:8000/nodes
```

Explain:

> “The controller runs a heartbeat monitor. When it stops receiving heartbeats from worker3 for more than the timeout, it marks it as DOWN and triggers rebalancing.”

4. Show new mapping for `user123`:

```bash
curl "http://localhost:8000/mapping?key=user123"
```

Now only **UP** workers will appear.

5. Check the key on each mapped worker (on correct ports):

```bash
curl "http://localhost:8101/kv?key=user123"
curl "http://localhost:8201/kv?key=user123"
curl "http://localhost:8401/kv?key=user123"
```

Explain:

> “Even though worker3 is permanently down, the key is still stored on the nodes that the new mapping assigns. Rebalancing happens in the background when a worker goes down.”

That’s your **main story**: consistency + replication + failure handling.

---

### Step 5 – Optional “scaling” demo

You can show that workers are independent and can be scaled.

Example: scale worker2 to 2 replicas:

```bash
kubectl scale deployment worker2 -n kv-system --replicas=2
kubectl get pods -n kv-system
```

Explain:

> “I can horizontally scale individual worker deployments. In a more advanced setup, I can attach an HPA (HorizontalPodAutoscaler) to auto-scale based on CPU or custom load metrics.”

You don’t need to fully implement HPA unless you want extra marks.

---

## 2️⃣ What you should say as architecture summary (in viva)

Keep this in your head (or write as notes):

* One **controller** microservice:

  * Maintains worker registry
  * Exposes REST `/register`, `/heartbeat`, `/mapping`, `/nodes`
  * Uses **consistent hashing** to map keys to primary + 2 replicas
  * Runs background task to detect failed nodes using heartbeat timeouts
  * Notifies workers via `/node_down` to trigger rebalancing

* Four **worker** microservices:

  * In-memory key–value store
  * Auto-register with controller on startup
  * Send periodic heartbeats
  * On `PUT /kv`:

    * If primary → write locally, sync replicate to one, async to another
    * Enforce write quorum of 2
  * On `GET /kv` → read from local store
  * On `/node_down` → background rebalancing: for each local key, query mapping and ensure replicas are updated

* **Kubernetes**:

  * Controller and each worker run as separate Deployments + Services in namespace `kv-system`
  * Minikube used as local cluster
  * Failure simulated via `kubectl scale deployment ... --replicas=0`

---

## 3️⃣ Suggested Git commit for “k8s + demo ready”

After you create `DEMO.md` and finalize k8s files:

```bash
git add k8s DEMO.md
git commit -m "docs: add Kubernetes deployment and demo script for distributed KV store"
```

---


