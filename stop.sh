#!/usr/bin/env bash
set -e

NAMESPACE="kv-system"

kubectl delete -f k8s/ --ignore-not-found=true
kubectl delete namespace "$NAMESPACE" --ignore-not-found=true

kubectl get pods -A
echo "Hey the KV System has been stopped successfully!"