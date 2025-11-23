#!/usr/bin/env bash
set -e

NAMESPACE="kv-system"

minikube start --driver=docker
eval "$(minikube docker-env)"

kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
kubectl wait namespace/"$NAMESPACE" --for=delete --timeout=60s || true

kubectl apply -f k8s/namespace.yaml

docker build -t distributed-kv-controller:latest ./controller
docker build -t distributed-kv-worker:latest ./worker

kubectl apply -f k8s/

kubectl get pods -n "$NAMESPACE"
echo "Hey the KV Data Base System has been started successfully!"