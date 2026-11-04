# API Contract
POST /v1/documents/process — multipart file; include_raw_text=false by default.
GET /v1/documents/schemas — schema registry.
GET /v1/documents/schemas/{document_type} — fetch one schema.
GET /v1/system/capabilities — formats, types and limits.
GET /ready — readiness.
Success returns request_id, status, document, classification, extracted_data, tables, pages, validation, review_required, processing and warnings. Field confidence is null where field-level confidence is not reliably measurable; page OCR confidence is supplied in page metadata. Errors: 400 invalid content, 413 configured limits, 415 unsupported type, 422 processing failure, 404 unknown schema.


## Quality and review decision metadata (v1.1)

The response includes additive fields:
- `completeness`: expected, extracted and missing schema fields. PAN expected fields currently include PAN number, holder name, parent name and date of birth. These are review expectations; only schema `required` fields create validation errors.
- `quality.document_ocr_confidence`: mean of available page-level OCR scores. This is a document-level signal, not field-level confidence.
- `quality.ocr_review_threshold`: configurable review threshold (`DOCINTEL_REVIEW_OCR_CONFIDENCE_THRESHOLD`, default 70).
- `quality.field_confidence_available`: false until calibrated field-level confidence is implemented.
- `processing_decision.status`: `AUTO_ACCEPT`, `REVIEW_REQUIRED` or `REUPLOAD_REQUIRED`.
- `processing_decision.reason_codes` and `required_actions`: machine-readable review rationale.
- `pipeline_version`: processing pipeline version.

A low document OCR score triggers review; it does not prove an individual extracted field is incorrect. AUTO_ACCEPT is a technical extraction decision only and must not be treated as identity verification or proof of document authenticity.