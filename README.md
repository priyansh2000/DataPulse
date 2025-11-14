# Distributed KV - Python prototype

Requirements: Docker, Docker Compose

Build and start:
docker-compose up --build

Controller API:
GET http://localhost:8000/nodes
GET http://localhost:8000/mapping?key=somekey

Workers:
PUT http://localhost:8101/kv  body {"key":"k1","value":"v1"}
GET http://localhost:8101/kv?key=k1

Test flow:
1. Start system: docker-compose up --build
2. Wait a few seconds for workers to register.
3. curl http://localhost:8000/nodes
4. curl "http://localhost:8000/mapping?key=hello"
5. Use mapping to PUT/GET from a worker.
