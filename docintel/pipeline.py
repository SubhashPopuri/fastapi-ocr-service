"""End-to-end processing orchestration."""
import os
import time
import uuid

from .processors import process_pdf, process_image, process_other
from .classification import classify
from .extraction import extract_fields, validate_fields
from .models import DocumentResponse

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def process_document(filename, data, media_type, include_raw_text=False):
    start = time.perf_counter()
    suffix = os.path.splitext(filename.lower())[1]
    result = (
        process_pdf(data) if suffix == ".pdf"
        else process_image(data) if suffix in IMAGE_EXT
        else process_other(data, suffix)
    )
    classification = classify(result["text"])
    fields = extract_fields(
        result["text"], classification["document_type"], result["pages"], result.get("tables")
    )
    validation = validate_fields(fields, classification["document_type"])
    review = classification["review_required"] or bool(validation["errors"]) or bool(validation["warnings"])
    payload = {
        "request_id": "req_" + uuid.uuid4().hex,
        "status": "success" if result["text"].strip() or result["tables"] else "completed_with_warnings",
        "document": {
            "filename": filename, "media_type": media_type,
            "document_type": classification["document_type"],
            "page_count": result["page_count"], "size_bytes": len(data),
        },
        "classification": classification,
        "extracted_data": fields,
        "tables": result["tables"],
        "pages": [
            {
                "page": page["page"], "method": page["method"],
                "ocr_confidence": page.get("ocr_confidence"),
                "text_length": len(page.get("text", "")),
            }
            for page in result["pages"]
        ],
        "validation": validation,
        "review_required": review,
        "processing": {
            "methods": result["methods"],
            "ocr_used": "tesseract_ocr" in result["methods"],
            "duration_ms": round((time.perf_counter() - start) * 1000),
        },
        "warnings": result["warnings"] + ([] if result["text"].strip() else ["No readable text was extracted."]),
    }
    if include_raw_text:
        payload["raw_text"] = result["text"]
    response = DocumentResponse(**payload).dict()
    if not include_raw_text:
        response.pop("raw_text", None)
    return response
