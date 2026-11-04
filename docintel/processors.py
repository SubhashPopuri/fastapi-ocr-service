"""Format-specific processors for PDF, images and office/text files."""
from io import BytesIO
import csv
import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from .config import get_settings
def _ocr(image):
    if get_settings().tesseract_cmd: pytesseract.pytesseract.tesseract_cmd=get_settings().tesseract_cmd
    image=image.convert("RGB")
    d=pytesseract.image_to_data(image,lang=get_settings().ocr_language,output_type=pytesseract.Output.DICT,timeout=45)
    text=pytesseract.image_to_string(image,lang=get_settings().ocr_language,timeout=45)
    scores=[]
    for x in d.get("conf",[]):
        try:
            n=float(x)
            if n>=0: scores.append(n)
        except (ValueError,TypeError): pass
    return text.strip(),round(sum(scores)/len(scores),2) if scores else None
def process_pdf(data):
    pages=[]; tables=[]; methods=[]; warnings=[]
    with pdfplumber.open(BytesIO(data)) as pdf:
        if len(pdf.pages)>get_settings().max_pdf_pages: raise ValueError(f"PDF page limit exceeded ({get_settings().max_pdf_pages}).")
        for number,page in enumerate(pdf.pages,1):
            text=(page.extract_text() or "").strip(); method="pdf_text"; conf=None
            if len(text)<25:
                try:
                    imgs=convert_from_bytes(data,dpi=get_settings().ocr_dpi,first_page=number,last_page=number,fmt="png")
                    if imgs:
                        ocr_text,conf=_ocr(imgs[0])
                        if len(ocr_text)>len(text): text,method=ocr_text,"tesseract_ocr"
                except Exception as exc: warnings.append(f"Page {number} OCR failed/unavailable ({type(exc).__name__}).")
            pages.append({"page":number,"text":text,"method":method,"ocr_confidence":conf}); methods.append(method)
            try:
                for ti,table in enumerate(page.extract_tables() or [],1):
                    rows=[[c.strip() if isinstance(c,str) else c for c in row] for row in table if row]
                    if rows: tables.append({"page":number,"table_index":ti,"rows":rows})
            except Exception: warnings.append(f"Table extraction failed on page {number}.")
    return {"text":"\n\n".join(p["text"] for p in pages),"pages":pages,"page_count":len(pages),"tables":tables,"methods":sorted(set(methods)),"warnings":warnings}
def process_image(data):
    text,conf=_ocr(Image.open(BytesIO(data)))
    return {"text":text,"pages":[{"page":1,"text":text,"method":"tesseract_ocr","ocr_confidence":conf}],"page_count":1,"tables":[],"methods":["tesseract_ocr"],"warnings":[]}
def process_other(data,suffix):
    tables=[]; text=""
    if suffix==".txt": text=data.decode("utf-8-sig",errors="replace")
    elif suffix==".csv":
        rows=list(csv.reader(data.decode("utf-8-sig",errors="replace").splitlines()))
        if rows: tables=[{"page":1,"table_index":1,"rows":rows}]
        text="\n".join(" | ".join(row) for row in rows)
    elif suffix==".docx":
        from docx import Document
        doc=Document(BytesIO(data)); parts=[p.text for p in doc.paragraphs if p.text.strip()]
        for i,t in enumerate(doc.tables,1):
            rows=[[c.text.strip() for c in r.cells] for r in t.rows]; tables.append({"page":1,"table_index":i,"rows":rows}); parts.extend(" | ".join(r) for r in rows)
        text="\n".join(parts)
    elif suffix==".xlsx":
        from openpyxl import load_workbook
        wb=load_workbook(BytesIO(data),read_only=True,data_only=True); parts=[]
        for sheet in wb.worksheets:
            rows=[[str(v) if v is not None else "" for v in row] for row in sheet.iter_rows(values_only=True)]; rows=[r for r in rows if any(r)]
            if rows: tables.append({"page":1,"table_index":len(tables)+1,"sheet":sheet.title,"rows":rows})
            parts.extend(" | ".join(r) for r in rows)
        text="\n".join(parts)
    return {"text":text,"pages":[{"page":1,"text":text,"method":"native_text","ocr_confidence":None}],"page_count":1,"tables":tables,"methods":["native_text"],"warnings":[]}
