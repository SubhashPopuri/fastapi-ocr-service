"""Versioned FastAPI routes with optional API-key protection."""
import secrets

from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Security
from fastapi.concurrency import run_in_threadpool
from fastapi.security import APIKeyHeader

from .ingestion import read_upload
from .pipeline import process_document
from .schemas import list_schemas, SCHEMAS
from .config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)):
    """Require X-API-Key when DOCINTEL_API_KEY is configured.

    Local development remains frictionless when the environment variable is
    unset. Hosted deployments should always configure a generated secret.
    """
    expected = get_settings().api_key
    if expected and (not api_key or not secrets.compare_digest(api_key, expected)):
        raise HTTPException(status_code=401, detail="Missing or invalid API key.")


# Keep health checks public so Render can verify the service without a secret.
router = APIRouter(tags=["Document Intelligence"])


@router.post(
    "/v1/documents/process",
    summary="Process PDF, image, Word, Excel, CSV or text file",
    dependencies=[Security(require_api_key)],
)
async def process(
    file: UploadFile = File(...),
    include_raw_text: bool = Query(False, description="Return full extracted text; disabled by default"),
):
    try:
        filename, data, media = await read_upload(file)
        return await run_in_threadpool(process_document, filename, data, media, include_raw_text)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(422, f"Processing failed ({type(exc).__name__}). Check server diagnostics.")
    finally:
        await file.close()


@router.get("/v1/documents/schemas", dependencies=[Security(require_api_key)])
def schemas():
    return {"schemas": list_schemas()}


@router.get("/v1/documents/schemas/{document_type}", dependencies=[Security(require_api_key)])
def schema(document_type: str):
    if document_type not in SCHEMAS:
        raise HTTPException(404, "Unknown document type.")
    return {"document_type": document_type, **SCHEMAS[document_type]}


@router.get("/v1/system/capabilities", dependencies=[Security(require_api_key)])
def capabilities():
    s = get_settings()
    return {
        "service": "Document Intelligence Platform",
        "version": "1.1.0",
        "formats": ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "txt", "csv", "docx", "xlsx", "json", "xml", "html", "md", "log", "yaml", "yml"],
        "document_types": list(SCHEMAS),
        "ocr": {"provider": "Tesseract", "language": s.ocr_language},
        "limits": {
            "max_upload_bytes": s.max_upload_bytes,
            "max_pdf_pages": s.max_pdf_pages,
            "max_image_pixels": s.max_image_pixels,
        },
    }


@router.get("/ready", tags=["Health"])
def ready():
    return {"status": "ready"}
