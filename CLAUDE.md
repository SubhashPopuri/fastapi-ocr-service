# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI OCR Service is a REST API microservice for extracting text from PDF files and images using OCR. Supports hybrid PDF extraction (pdfplumber + OCR fallback), image preprocessing pipeline, and bilingual documentation (English/Russian).

**Key Characteristics:**
- Single-file application (`main.py`, ~565 lines)
- Stateless, no database
- Production-ready with Nginx/SSL deployment documentation

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-rus poppler-utils

# Run the service
python main.py
# → http://localhost:8000
# → Swagger UI: http://localhost:8000/docs
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:8000/

# Image OCR with preprocessing
curl -X POST "http://localhost:8000/image?preprocess=grayscale,denoise,binarize" \
  -F "file=@test.jpg"

# PDF with auto OCR fallback
curl -X POST "http://localhost:8000/pdf" -F "file=@document.pdf"

# Force OCR on PDF
curl -X POST "http://localhost:8000/pdf?force_ocr=true&ocr_language=rus" \
  -F "file=@scan.pdf"
```

## Architecture

```
Client → Nginx (SSL) → Uvicorn:8000 → FastAPI Application
                                              ↓
                         ┌────────────────────┼────────────────────┐
                         ↓                    ↓                    ↓
                   POST /image          POST /pdf             GET /
                   (Tesseract +      (pdfplumber →        (Health check)
                   preprocessing)    OCR fallback)
```

### main.py Structure

| Section | Lines | Purpose |
|---------|-------|---------|
| Imports & config | 1-22 | Dependencies, Tesseract path, FastAPI app |
| Preprocessing functions | 29-171 | `_to_grayscale`, `_denoise`, `_deskew`, `_binarize`, `_upscale`, `_apply_clahe`, `preprocess_image` |
| PDF OCR functions | 178-310 | `_extract_with_pdfplumber`, `_pdf_to_images`, `_extract_with_ocr`, `_needs_ocr_fallback` |
| API Endpoints | 317-559 | `GET /`, `POST /pdf`, `POST /image` |

### Hybrid PDF Extraction Flow

1. Try pdfplumber extraction first (fast, preserves layout)
2. Check fallback conditions via `_needs_ocr_fallback()`:
   - Total chars < 100
   - Avg chars/page < threshold (default: 50)
   - >50% pages empty
3. If conditions met → render PDF to images via PyMuPDF → run Tesseract OCR

### Image Preprocessing Pipeline

Steps are applied in order specified. Available steps:
- `upscale` - Enlarge small images (uses `upscale_min` parameter)
- `grayscale` - Convert to single channel
- `denoise` - Non-local means denoising
- `deskew` - Correct rotation angle
- `clahe` - Adaptive histogram equalization
- `contrast` - Standard histogram equalization
- `binarize` - Otsu/adaptive thresholding

Recommended order: `upscale,grayscale,denoise,deskew,clahe,binarize`

## Key Implementation Details

1. **Tesseract path** (lines 14-17): Hardcoded to `/usr/bin/tesseract`

2. **OCR confidence** (lines 256-264): Calculated from `pytesseract.image_to_data()`, excludes -1 values

3. **PSM modes**: `/image` endpoint accepts comma-separated PSM values for comparison (e.g., `psm=3,6,11`)

4. **Error handling pattern**:
   - 400: Invalid file format or parameters
   - 500: Processing failures
   - Per-page errors logged as warnings, processing continues

## Dependencies

**Python** (requirements.txt):
- FastAPI, Uvicorn, pytesseract, pdfplumber, Pillow
- pdf2image - PDF to image conversion (uses poppler)
- opencv-python-headless - Image preprocessing
- deskew - Skew angle detection

**System**:
- Tesseract OCR binary
- Language packs (tesseract-ocr-rus for Russian)
- poppler-utils (for pdf2image)

## Adding New Endpoints

Follow existing pattern:
1. `async def endpoint_name(file: UploadFile, ...)`
2. Validate file format early
3. Use try/except with HTTPException
4. Return JSONResponse with `{"status": "success", ...}`
5. Close file in finally block: `await file.close()`

## Deployment

See DEPLOYMENT.md for:
- Systemd service configuration
- Nginx reverse proxy with SSL/TLS (Certbot)
- DuckDNS dynamic DNS setup
