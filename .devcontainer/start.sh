#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/fastapi-ocr-service

if ! command -v tesseract >/dev/null 2>&1; then
  echo "ERROR: Tesseract is not installed."
  exit 1
fi

if ! command -v pdfinfo >/dev/null 2>&1; then
  echo "ERROR: Poppler is not installed (pdfinfo command missing)."
  exit 1
fi

if pgrep -f '[.]venv/bin/python main.py' >/dev/null 2>&1; then
  echo "FastAPI OCR service is already running."
  exit 0
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Python virtual environment is missing. Re-run the Codespaces post-create setup."
  exit 1
fi

nohup .venv/bin/python main.py > /tmp/fastapi-ocr.log 2>&1 &
echo "Started FastAPI OCR service. Logs: /tmp/fastapi-ocr.log"
