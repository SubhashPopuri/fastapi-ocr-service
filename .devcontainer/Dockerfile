FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       tesseract-ocr \
       tesseract-ocr-eng \
       tesseract-ocr-rus \
       poppler-utils \
       libgl1 \
       libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
