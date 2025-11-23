#!/usr/bin/env bash

curl -s http://localhost:8000/nodes
echo
curl -s http://localhost:8101/status
echo
curl -s http://localhost:8201/status
echo
curl -s http://localhost:8301/status
echo
curl -s http://localhost:8401/status
