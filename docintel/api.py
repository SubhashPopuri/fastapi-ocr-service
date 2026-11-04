"""Versioned FastAPI routes."""
from fastapi import APIRouter,File,UploadFile,HTTPException,Query
from fastapi.concurrency import run_in_threadpool
from .ingestion import read_upload
from .pipeline import process_document
from .schemas import list_schemas,SCHEMAS
from .config import get_settings
router=APIRouter(tags=["Document Intelligence"])
@router.post("/v1/documents/process",summary="Process PDF, image, Word, Excel, CSV or text file")
async def process(file:UploadFile=File(...),include_raw_text:bool=Query(False,description="Return full extracted text; disabled by default")):
    filename,data,media=await read_upload(file)
    try: return await run_in_threadpool(process_document,filename,data,media,include_raw_text)
    except HTTPException: raise
    except ValueError as exc: raise HTTPException(422,str(exc))
    except Exception as exc: raise HTTPException(422,f"Processing failed ({type(exc).__name__}). Check server diagnostics.")
    finally: await file.close()
@router.get("/v1/documents/schemas")
def schemas(): return {"schemas":list_schemas()}
@router.get("/v1/documents/schemas/{document_type}")
def schema(document_type:str):
    if document_type not in SCHEMAS: raise HTTPException(404,"Unknown document type.")
    return {"document_type":document_type,**SCHEMAS[document_type]}
@router.get("/v1/system/capabilities")
def capabilities():
    s=get_settings()
    return {"service":"Document Intelligence Platform","version":"1.0.0","formats":["pdf","png","jpg","jpeg","tiff","bmp","txt","csv","docx","xlsx"],"document_types":list(SCHEMAS),"ocr":{"provider":"Tesseract","language":s.ocr_language},"limits":{"max_upload_bytes":s.max_upload_bytes,"max_pdf_pages":s.max_pdf_pages,"max_image_pixels":s.max_image_pixels}}
@router.get("/ready",tags=["Health"])
def ready(): return {"status":"ready"}
