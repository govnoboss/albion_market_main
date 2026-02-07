#!/bin/bash
# GBot License Server - Deployment Script

echo "=== Installing dependencies ==="
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

echo "=== Creating virtual environment ==="
python3 -m venv venv
source venv/bin/activate

echo "=== Installing Python packages ==="
pip install -r requirements.txt

echo "=== Starting server ==="
echo "Run: uvicorn main:app --host 0.0.0.0 --port 8000"
