"""Format-specific processors for PDF, images and office/text files."""
from io import BytesIO
import csv
import json
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from .config import get_settings

def _ocr(image):
    if get_settings().tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd=get_settings().tesseract_cmd
    image=image.convert("RGB")
    data=pytesseract.image_to_data(image,lang=get_settings().ocr_language,output_type=pytesseract.Output.DICT,timeout=45)
    text=pytesseract.image_to_string(image,lang=get_settings().ocr_language,timeout=45)
    scores=[]
    for item in data.get("conf",[]):
        try:
            score=float(item)
            if score>=0: scores.append(score)
        except (ValueError,TypeError): pass
    return text.strip(),round(sum(scores)/len(scores),2) if scores else None

def process_pdf(data):
    pages=[]; tables=[]; methods=[]; warnings=[]
    with pdfplumber.open(BytesIO(data)) as pdf:
        if len(pdf.pages)>get_settings().max_pdf_pages:
            raise ValueError(f"PDF page limit exceeded ({get_settings().max_pdf_pages}).")
        for number,page in enumerate(pdf.pages,1):
            text=(page.extract_text() or "").strip()
            method="pdf_text"; confidence=None
            if len(text)<25:
                try:
                    images=convert_from_bytes(data,dpi=get_settings().ocr_dpi,first_page=number,last_page=number,fmt="png")
                    if images:
                        ocr_text,ocr_confidence=_ocr(images[0])
                        if len(ocr_text)>len(text):
                            text,method,confidence=ocr_text,"tesseract_ocr",ocr_confidence
                except Exception as exc:
                    warnings.append(f"Page {number} OCR failed or unavailable ({type(exc).__name__}).")
            pages.append({"page":number,"text":text,"method":method,"ocr_confidence":confidence})
            methods.append(method)
            try:
                for table_index,table in enumerate(page.extract_tables() or [],1):
                    rows=[[cell.strip() if isinstance(cell,str) else cell for cell in row] for row in table if row]
                    if rows: tables.append({"page":number,"table_index":table_index,"rows":rows})
            except Exception:
                warnings.append(f"Table extraction failed on page {number}.")
    return {"text":"\n\n".join(page["text"] for page in pages),"pages":pages,"page_count":len(pages),"tables":tables,"methods":sorted(set(methods)),"warnings":warnings}

def process_image(data):
    text,confidence=_ocr(Image.open(BytesIO(data)))
    return {"text":text,"pages":[{"page":1,"text":text,"method":"tesseract_ocr","ocr_confidence":confidence}],"page_count":1,"tables":[],"methods":["tesseract_ocr"],"warnings":[]}

def process_other(data,suffix):
    tables=[]; text=""
    if suffix in {".txt",".md",".log",".yaml",".yml"}:
        text=data.decode("utf-8-sig",errors="replace")
    elif suffix==".json":
        raw=data.decode("utf-8-sig",errors="replace")
        try:
            parsed=json.loads(raw); lines=[]
            def flatten(value,prefix=""):
                if isinstance(value,dict):
                    for key,item in value.items(): flatten(item,str(key).replace("_"," "))
                elif isinstance(value,list):
                    for item in value: flatten(item,prefix)
                elif prefix:
                    lines.append(f"{prefix}: {value}")
            flatten(parsed); text="\n".join(lines) if lines else json.dumps(parsed,ensure_ascii=False,indent=2)
        except json.JSONDecodeError: text=raw
    elif suffix==".xml":
        raw=data.decode("utf-8-sig",errors="replace")
        try:
            root=ET.fromstring(raw); lines=[]
            for element in root.iter():
                if element.text and element.text.strip():
                    label=element.tag.split("}")[-1].replace("_"," ")
                    lines.append(f"{label}: {element.text.strip()}")
            text="\n".join(lines)
        except ET.ParseError: text=raw
    elif suffix in {".html",".htm"}:
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts=[]
            def handle_data(self,value):
                if value.strip(): self.parts.append(value.strip())
        parser=TextExtractor()
        parser.feed(data.decode("utf-8-sig",errors="replace"))
        text="\n".join(parser.parts)
    elif suffix==".csv":
        rows=list(csv.reader(data.decode("utf-8-sig",errors="replace").splitlines()))
        if rows: tables=[{"page":1,"table_index":1,"rows":rows}]
        text="\n".join(" | ".join(row) for row in rows)
    elif suffix==".docx":
        from docx import Document
        document=Document(BytesIO(data))
        parts=[paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        for index,table in enumerate(document.tables,1):
            rows=[[cell.text.strip() for cell in row.cells] for row in table.rows]
            tables.append({"page":1,"table_index":index,"rows":rows})
            parts.extend(" | ".join(row) for row in rows)
        text="\n".join(parts)
    elif suffix==".xlsx":
        from openpyxl import load_workbook
        workbook=load_workbook(BytesIO(data),read_only=True,data_only=True)
        parts=[]
        for sheet in workbook.worksheets:
            rows=[[str(value) if value is not None else "" for value in row] for row in sheet.iter_rows(values_only=True)]
            rows=[row for row in rows if any(row)]
            if rows: tables.append({"page":1,"table_index":len(tables)+1,"sheet":sheet.title,"rows":rows})
            parts.extend(" | ".join(row) for row in rows)
        text="\n".join(parts)
    return {"text":text,"pages":[{"page":1,"text":text,"method":"native_text","ocr_confidence":None}],"page_count":1,"tables":tables,"methods":["native_text"],"warnings":[]}
