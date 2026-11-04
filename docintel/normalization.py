"""Conservative value normalization; original extracted value is always retained."""
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime

AMOUNT_FIELDS = {
    "total_amount", "tax_amount", "subtotal", "cgst_amount", "sgst_amount",
    "igst_amount", "total_tax", "grand_total", "amount_due", "unit_price",
    "line_amount", "net_pay", "gross_pay", "deductions",
    "opening_balance", "closing_balance",
}
DATE_FIELDS = {
    "invoice_date", "due_date", "po_date", "effective_date", "expiry_date",
    "document_date",
}


def normalize_value(field, value):
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if field == "email":
        return raw.lower()
    if field == "phone":
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 12 and digits.startswith("91"):
            return "+91" + digits[2:]
        if len(digits) == 10:
            return digits
        return None
    if field in AMOUNT_FIELDS:
        candidate = re.sub(r"[^\d,.\-]", "", raw).replace(",", "")
        try:
            return format(Decimal(candidate).quantize(Decimal("0.01")), "f")
        except (InvalidOperation, ValueError):
            return None
    if field in DATE_FIELDS:
        # ISO and year-first formats are unambiguous.
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                pass

        # Month-name formats such as 04-Nov-2026 are unambiguous.
        for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d %b %Y", "%d %B %Y",
                    "%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                pass

        # Numeric day/month formats are accepted only when the ordering is clear.
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
            try:
                parsed = datetime.strptime(raw, fmt)
                parts = re.split(r"[/-]", raw)
                if int(parts[0]) <= 12 and int(parts[1]) <= 12:
                    return None
                return parsed.date().isoformat()
            except (ValueError, IndexError):
                pass
        return None
    return re.sub(r"\s+", " ", raw).strip() or None


def normalize_fields(fields):
    for key, item in fields.items():
        if key == "line_items" or isinstance(item.get("value"), (list, dict)):
            item["normalized_value"] = None
        else:
            item["normalized_value"] = normalize_value(key, item.get("value"))
    return fields
