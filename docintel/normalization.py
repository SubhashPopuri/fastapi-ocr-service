"""Conservative value normalization; original extracted value is always retained."""
import re
from decimal import Decimal,InvalidOperation
from datetime import datetime
AMOUNT_FIELDS={"total_amount","tax_amount","net_pay","gross_pay","deductions","opening_balance","closing_balance"}
DATE_FIELDS={"invoice_date","due_date","po_date","effective_date","expiry_date","document_date"}
def normalize_value(field,value):
    raw=str(value).strip()
    if field=="email": return raw.lower()
    if field=="phone":
        cleaned=re.sub(r"[^\d+]","",raw)
        return cleaned if len(re.sub(r"\D","",cleaned))>=8 else None
    if field in AMOUNT_FIELDS:
        candidate=re.sub(r"[^\d,.\-]","",raw).replace(",","")
        try: return format(Decimal(candidate).quantize(Decimal("0.01")),"f")
        except (InvalidOperation,ValueError): return None
    if field in DATE_FIELDS:
        for fmt in ("%Y-%m-%d","%Y/%m/%d"):
            try: return datetime.strptime(raw,fmt).date().isoformat()
            except ValueError: pass
        for fmt in ("%d/%m/%Y","%d-%m-%Y","%d/%m/%y","%d-%m-%y"):
            try:
                parsed=datetime.strptime(raw,fmt)
                # Do not guess when both day and month could be valid month numbers.
                parts=re.split(r"[/-]",raw)
                if int(parts[0])<=12 and int(parts[1])<=12: return None
                return parsed.date().isoformat()
            except (ValueError,IndexError): pass
        return None
    return re.sub(r"\s+"," ",raw).strip() or None
def normalize_fields(fields):
    for key,item in fields.items():
        item["normalized_value"]=normalize_value(key,item.get("value",""))
    return fields
