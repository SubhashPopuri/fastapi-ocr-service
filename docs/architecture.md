# Architecture
FastAPI intake -> signature/size validation -> format processors -> classification -> schema-guided extraction -> normalization/validation -> canonical response.
PDF uses pdfplumber and page-specific Tesseract fallback. Images use Tesseract. DOCX/XLSX/CSV/TXT use native parsers. PDF/Office/CSV table-like structures are returned as rows where supported. Classification is explainable keyword matching; confidence remains null because rule strength is not calibrated. Ambiguous/unknown documents request human review.
Modules: api, config, ingestion, processors, classification, schemas, extraction, normalization, pipeline and models.
Production hardening still required: authentication, authorization, tenant isolation, malware scanning, audit/retention controls, rate limits, durable jobs, monitoring and load testing.
