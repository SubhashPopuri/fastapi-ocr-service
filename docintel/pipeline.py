"""End-to-end processing orchestration."""
import os
import time
import uuid

from .processors import process_pdf, process_image, process_other
from .classification import classify
from .extraction import extract_fields, validate_fields
from .models import DocumentResponse
from .schemas import SCHEMAS
from .config import get_settings

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
    schema = SCHEMAS.get(classification["document_type"], SCHEMAS["general_document"])
    expected_fields = schema.get("expected", schema.get("required", []))
    extracted_expected = [key for key in expected_fields if key in fields and fields[key].get("value") not in (None, "")]
    missing_expected = [key for key in expected_fields if key not in extracted_expected]
    page_scores = [page.get("ocr_confidence") for page in result["pages"] if isinstance(page.get("ocr_confidence"), (int, float))]
    document_ocr_confidence = round(sum(page_scores) / len(page_scores), 2) if page_scores else None
    threshold = get_settings().review_ocr_confidence_threshold
    reason_codes = []
    required_actions = []
    if classification["review_required"]:
        reason_codes.append("DOCUMENT_CLASSIFICATION_UNCERTAIN")
    if missing_expected:
        reason_codes.append("EXPECTED_FIELDS_MISSING")
        required_actions.append("VERIFY_OR_COMPLETE_MISSING_FIELDS")
    if validation["errors"]:
        reason_codes.append("VALIDATION_ERRORS")
        required_actions.append("CORRECT_INVALID_FIELDS")
    if validation["warnings"]:
        reason_codes.append("VALIDATION_WARNINGS")
        required_actions.append("VERIFY_WARNING_FIELDS")
    if document_ocr_confidence is not None and document_ocr_confidence < threshold:
        reason_codes.append("LOW_DOCUMENT_OCR_QUALITY")
        required_actions.append("VERIFY_EXTRACTED_FIELDS")
    no_readable_content = not result["text"].strip() and not result["tables"]
    if no_readable_content:
        reason_codes.append("NO_READABLE_CONTENT")
        required_actions.append("UPLOAD_CLEARER_DOCUMENT")
    review = bool(reason_codes)
    decision_status = "REUPLOAD_REQUIRED" if no_readable_content else "REVIEW_REQUIRED" if review else "AUTO_ACCEPT"
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
        "completeness": {
            "expected_fields": len(expected_fields),
            "extracted_fields": len(extracted_expected),
            "missing_fields": missing_expected,
        },
        "quality": {
            "document_ocr_confidence": document_ocr_confidence,
            "ocr_review_threshold": threshold,
            "field_confidence_available": False,
        },
        "processing_decision": {
            "status": decision_status,
            "reason_codes": reason_codes,
            "required_actions": list(dict.fromkeys(required_actions)),
        },
        "pipeline_version": "1.1.0",
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
