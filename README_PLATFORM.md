# Document Intelligence Platform

Self-hosted FastAPI service for PDF (digital/scanned), PNG/JPG/TIFF/BMP, DOCX, XLSX, CSV and TXT.

## Ubuntu / Codespaces setup
\`\`\`bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr poppler-utils
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
\`\`\`

Open Swagger UI at /docs.

## Process a file
\`\`\`bash
curl -X POST http://localhost:8000/v1/documents/process -F 'file=@invoice.pdf'
\`\`\`

Use include_raw_text=true only when full extracted text is required.

## Tests
\`\`\`bash
pip install -r requirements-dev.txt
pytest -q
\`\`\`

## Docker
\`\`\`bash
cp .env.example .env
docker compose up --build
\`\`\`

Classification and extraction are deterministic baseline rules, not guaranteed interpretation of arbitrary layouts. Human-review ambiguous outputs. See docs/security.md.
