#!/usr/bin/env bash

echo "Port-forward processes:"
ps aux | grep "kubectl port-forward" | grep -v grep
echo
echo "Kubernetes pods:"
kubectl get pods -n kv-system
echo "Hey the KV Data Base System status has been displayed successfully!"