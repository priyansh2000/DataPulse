#!/usr/bin/env bash

kubectl logs -n kv-system -l app=controller -f &
kubectl logs -n kv-system -l app=worker1 -f &
kubectl logs -n kv-system -l app=worker2 -f &
kubectl logs -n kv-system -l app=worker3 -f &
kubectl logs -n kv-system -l app=worker4 -f &
wait
