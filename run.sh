#!/bin/bash
# Run without Docker
cd "$(dirname "$0")"
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
