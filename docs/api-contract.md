# API Contract
POST /v1/documents/process — multipart file; include_raw_text=false by default.
GET /v1/documents/schemas — schema registry.
GET /v1/documents/schemas/{document_type} — fetch one schema.
GET /v1/system/capabilities — formats, types and limits.
GET /ready — readiness.
Success returns request_id, status, document, classification, extracted_data, tables, pages, validation, review_required, processing and warnings. Field confidence is null where field-level confidence is not reliably measurable; page OCR confidence is supplied in page metadata. Errors: 400 invalid content, 413 configured limits, 415 unsupported type, 422 processing failure, 404 unknown schema.
