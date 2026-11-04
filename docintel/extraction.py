"""Schema-guided field extraction with page evidence and validation."""
import re
from .schemas import SCHEMAS
from .normalization import normalize_fields
EMAIL=r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"
PHONE=r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)"
DATE=r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"
AMOUNT_FIELDS={"total_amount","tax_amount","net_pay","gross_pay","deductions","opening_balance","closing_balance"}
DATE_FIELDS={"invoice_date","due_date","po_date","effective_date","expiry_date","document_date"}
def _find(text,labels):
    for line in text.splitlines():
        for label in labels:
            m=re.search(r"^\s*"+re.escape(label)+r"\s*[:|#-]\s*(.+?)\s*$",line,re.I)
            if m and m.group(1).strip(): return m.group(1).strip(),line.strip()
    return None,None
def extract_fields(text,document_type,pages):
    schema=SCHEMAS.get(document_type,SCHEMAS["general_document"]); fields={}
    for key,labels in schema["fields"].items():
        value,evidence=_find(text,labels)
        if value:
            page=next((p["page"] for p in pages if evidence in p["text"]),None)
            fields[key]={"value":value,"normalized_value":None,"confidence":None,"source":{"page":page,"text":evidence[:300],"method":"label_pattern"},"validation_status":"not_checked","warnings":[]}
    for key,pattern in (("email",EMAIL),("phone",PHONE)):
        m=re.search(pattern,text,re.I)
        if m and key not in fields:
            value=m.group(0); page=next((p["page"] for p in pages if value in p["text"]),None)
            fields[key]={"value":value,"normalized_value":None,"confidence":None,"source":{"page":page,"text":value,"method":"pattern"},"validation_status":"not_checked","warnings":[]}
    return normalize_fields(fields)
def validate_fields(fields,document_type):
    schema=SCHEMAS.get(document_type,SCHEMAS["general_document"]); errors=[]; warnings=[]
    for key in schema["required"]:
        if key not in fields: errors.append({"field":key,"code":"required_missing","message":f"Required field '{key}' was not found."})
    for key,item in fields.items():
        value=str(item.get("value",""))
        if key=="email" and not re.fullmatch(EMAIL,value,re.I): errors.append({"field":key,"code":"invalid_format","message":"Email format is invalid."})
        if key in DATE_FIELDS and item.get("normalized_value") is None:
            warnings.append({"field":key,"code":"date_unrecognized","message":"Date could not be normalized unambiguously."})
        if key in AMOUNT_FIELDS and item.get("normalized_value") is None:
            warnings.append({"field":key,"code":"amount_unrecognized","message":"Amount could not be normalized."})
    for key,item in fields.items():
        item["validation_status"]="invalid" if any(e["field"]==key for e in errors) else "warning" if any(w["field"]==key for w in warnings) else "valid"
    return {"is_valid":not errors,"errors":errors,"warnings":warnings}
