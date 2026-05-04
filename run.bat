#!/bin/bash
# Run without Docker (Windows)
cd /d "%~dp0"
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
