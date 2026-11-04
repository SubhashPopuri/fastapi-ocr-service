"""Upload validation and content detection."""
from io import BytesIO
from zipfile import BadZipFile,ZipFile
import mimetypes
from PIL import Image,UnidentifiedImageError
from fastapi import HTTPException,UploadFile
from .config import get_settings
ALLOWED={".pdf",".png",".jpg",".jpeg",".tif",".tiff",".bmp",".txt",".csv",".docx",".xlsx"}
async def read_upload(upload:UploadFile):
    name=(upload.filename or "document").replace("\\","/").split("/")[-1]
    suffix=("."+name.rsplit(".",1)[-1].lower()) if "." in name else ""
    if suffix not in ALLOWED: raise HTTPException(415,"Unsupported file extension. Supported: PDF, images, TXT, CSV, DOCX and XLSX.")
    data=await upload.read(get_settings().max_upload_bytes+1)
    if not data: raise HTTPException(400,"Uploaded file is empty.")
    if len(data)>get_settings().max_upload_bytes: raise HTTPException(413,"File exceeds configured upload size limit.")
    return name,data,detect_type(data,suffix)
def detect_type(data:bytes,suffix:str):
    if suffix==".pdf":
        if not data.startswith(b"%PDF-"): raise HTTPException(400,"File content is not a valid PDF.")
        return "application/pdf"
    if suffix in {".png",".jpg",".jpeg",".tif",".tiff",".bmp"}:
        try:
            im=Image.open(BytesIO(data)); im.verify(); im=Image.open(BytesIO(data))
            if im.width*im.height>get_settings().max_image_pixels: raise HTTPException(413,"Image exceeds configured pixel limit.")
            return mimetypes.guess_type("file"+suffix)[0] or "application/octet-stream"
        except HTTPException: raise
        except (UnidentifiedImageError,OSError): raise HTTPException(400,"Invalid or corrupt image.")
    if suffix in {".docx",".xlsx"}:
        try:
            with ZipFile(BytesIO(data)) as z:
                names=set(z.namelist()); required="word/document.xml" if suffix==".docx" else "xl/workbook.xml"
                if required not in names: raise HTTPException(400,"File content does not match extension.")
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if suffix==".docx" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        except BadZipFile: raise HTTPException(400,"Invalid Office document.")
    return "text/csv" if suffix==".csv" else "text/plain"
