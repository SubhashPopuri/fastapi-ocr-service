"""Authenticated single-user demo portal proxy."""
import base64, hashlib, hmac, os, time
from pathlib import Path
import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
router = APIRouter()
COOKIE_NAME = "docintel_demo_session"
COOKIE_TTL_SECONDS = 8 * 60 * 60
HTML_PATH = Path(__file__).resolve().parent.parent / "webapp" / "index.html"
def _secret(): return os.getenv("DOCINTEL_DEMO_SESSION_SECRET", "").strip()
def _make_session():
    stamp = str(int(time.time())); sig = hmac.new(_secret().encode(), stamp.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(stamp.encode()+b"."+sig).decode().rstrip("=")
def _valid(token):
    if not token or not _secret(): return False
    try:
        raw=base64.urlsafe_b64decode(token+"="*(-len(token)%4)); stamp,sig=raw.split(b".",1); ts=int(stamp.decode())
        return ts <= int(time.time()) and int(time.time())-ts <= COOKIE_TTL_SECONDS and hmac.compare_digest(sig,hmac.new(_secret().encode(),stamp,hashlib.sha256).digest())
    except (ValueError,TypeError): return False
def _auth(request):
    if not _valid(request.cookies.get(COOKIE_NAME)): raise HTTPException(401,"Please sign in to the demo portal.")
@router.get("/app",include_in_schema=False)
async def home():
    if not HTML_PATH.exists(): raise HTTPException(503,"Demo web application is not installed.")
    return FileResponse(HTML_PATH,media_type="text/html")
@router.post("/app/login",include_in_schema=False)
async def login(response:Response,password:str=Form(...)):
    expected=os.getenv("DOCINTEL_DEMO_PASSWORD","")
    if not expected or not _secret(): raise HTTPException(503,"Demo portal credentials are not configured.")
    if not hmac.compare_digest(password,expected): raise HTTPException(401,"Incorrect demo password.")
    response.set_cookie(COOKIE_NAME,_make_session(),max_age=COOKIE_TTL_SECONDS,httponly=True,secure=(request.url.scheme == "https"),samesite="strict",path="/app")
    return {"status":"authenticated"}
@router.post("/app/logout",include_in_schema=False)
async def logout(request:Request,response:Response):
    response.delete_cookie(COOKIE_NAME,path="/app",secure=(request.url.scheme == "https"),httponly=True,samesite="strict"); return {"status":"logged_out"}
@router.get("/app/api/status",include_in_schema=False)
async def status(request:Request):
    _auth(request); upstream=os.getenv("DOCINTEL_UPSTREAM_API_URL","").rstrip("/"); key=os.getenv("DOCINTEL_API_KEY","")
    if not upstream or not key: raise HTTPException(503,"OCR API connection is not configured.")
    try:
        async with httpx.AsyncClient(timeout=20) as client: result=await client.get(upstream+"/v1/system/capabilities",headers={"X-API-Key":key})
        if result.status_code!=200: raise HTTPException(502,"OCR API health check failed.")
        return {"status":"connected","capabilities":result.json()}
    except httpx.HTTPError: raise HTTPException(502,"Unable to reach the OCR API.")
@router.post("/app/api/process",include_in_schema=False)
async def process(request:Request,file:UploadFile=File(...)):
    _auth(request); upstream=os.getenv("DOCINTEL_UPSTREAM_API_URL","").rstrip("/"); key=os.getenv("DOCINTEL_API_KEY","")
    if not upstream or not key: raise HTTPException(503,"OCR API connection is not configured.")
    content=await file.read(15*1024*1024+1)
    if len(content)>15*1024*1024: raise HTTPException(413,"File exceeds the 15 MB demo upload limit.")
    if not content: raise HTTPException(400,"Uploaded file is empty.")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(150.0,connect=15.0)) as client:
            result=await client.post(upstream+"/v1/documents/process",headers={"X-API-Key":key},files={"file":(file.filename or "upload",content,file.content_type or "application/octet-stream")})
        try: payload=result.json()
        except ValueError: payload={"detail":"OCR API returned a non-JSON response."}
        if result.status_code>=400:
            detail=payload.get("detail","OCR API processing failed.") if isinstance(payload,dict) else "OCR API processing failed."
            raise HTTPException(result.status_code,detail)
        return payload
    except httpx.TimeoutException: raise HTTPException(504,"OCR processing timed out. Try a smaller or lower-resolution document.")
    except httpx.HTTPError: raise HTTPException(502,"Unable to reach the OCR API.")
