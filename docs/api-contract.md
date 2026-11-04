# API Contract
POST /v1/documents/process — multipart field file; include_raw_text=false by default.
GET /v1/documents/schemas — schema registry.
GET /v1/documents/schemas/{document_type} — one schema.
GET /v1/system/capabilities — formats, types and configured limits.
GET /ready — readiness.
Success returns request_id, status, document, classification, extracted_data, tables, validation, review_required, processing and warnings. Field confidence is null when reliable field-level confidence is unavailable. Errors: 400 invalid content, 413 size/page/pixel limits, 415 unsupported type, 422 processing failure, 404 unknown schema.
