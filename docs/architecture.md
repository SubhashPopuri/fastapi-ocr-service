# Architecture
FastAPI intake -> signature/size validation -> format processors -> classification -> schema-guided extraction -> validation -> canonical response.
PDF uses pdfplumber and page-specific Tesseract fallback. Images use Tesseract. DOCX/XLSX/CSV/TXT use native parsers. Tables are returned as row arrays where supported. Classification is explainable keyword matching, not a calibrated ML probability. Unknown/ambiguous content requests human review.
Modules: api, config, ingestion, processors, classification, schemas, extraction, pipeline and models.
Production hardening still required: authentication, authorization, tenant isolation, malware scanning, audit/retention controls, rate limits, durable jobs, monitoring and load testing.
