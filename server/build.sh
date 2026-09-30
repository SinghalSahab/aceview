#!/usr/bin/env bash
# Exit on error
set -e

echo "==> Installing CPU-only PyTorch to prevent OOM on 512MB instances..."
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

echo "==> Installing project dependencies..."
pip install --no-cache-dir -r requirements.txt
