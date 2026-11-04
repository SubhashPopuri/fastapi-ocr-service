"""Environment-backed configuration."""
import os
class Settings:
    max_upload_bytes=int(os.getenv("DOCINTEL_MAX_UPLOAD_BYTES",15*1024*1024))
    max_pdf_pages=int(os.getenv("DOCINTEL_MAX_PDF_PAGES","30"))
    max_image_pixels=int(os.getenv("DOCINTEL_MAX_IMAGE_PIXELS","25000000"))
    ocr_dpi=int(os.getenv("DOCINTEL_OCR_DPI","250"))
    ocr_language=os.getenv("DOCINTEL_OCR_LANGUAGE","eng")
    tesseract_cmd=os.getenv("TESSERACT_CMD","")
settings=Settings()
def get_settings(): return settings
