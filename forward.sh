#!/usr/bin/env bash

kubectl port-forward svc/controller -n kv-system 8000:8000 &
kubectl port-forward svc/worker1 -n kv-system 8101:8001 &
kubectl port-forward svc/worker2 -n kv-system 8201:8001 &
kubectl port-forward svc/worker3 -n kv-system 8301:8001 &
kubectl port-forward svc/worker4 -n kv-system 8401:8001 &
echo "Port forwarding set up for controller and workers."