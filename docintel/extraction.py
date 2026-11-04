"""Schema-guided extraction with source evidence and conservative validation."""
import re
from decimal import Decimal, InvalidOperation

from .schemas import SCHEMAS
from .normalization import normalize_fields, normalize_value

EMAIL = r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"
PHONE = r"(?<!\d)(?:(?:\+?91)[\s().-]*)?[6-9](?:[\s().-]*\d){9}(?!\d)"
GSTIN = r"(?<![A-Z0-9])[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z](?![A-Z0-9])"
DATE_FIELDS = {"invoice_date", "due_date", "po_date", "effective_date", "expiry_date", "document_date"}
AMOUNT_FIELDS = {
    "total_amount", "tax_amount", "subtotal", "cgst_amount", "sgst_amount",
    "igst_amount", "total_tax", "grand_total", "amount_due", "unit_price",
    "line_amount", "net_pay", "gross_pay", "deductions", "opening_balance", "closing_balance",
}
PHONE_SKIP = ("invoice", "gstin", "hsn", "sac", "ifsc", "account number", "due date", "invoice date")


def _field(value, evidence, pages, method="label_pattern"):
    page = next((p["page"] for p in pages if evidence in p.get("text", "")), None)
    return {
        "value": value,
        "normalized_value": None,
        "confidence": None,
        "source": {"page": page, "text": evidence[:300], "method": method, "bounding_box": None},
        "validation_status": "not_checked",
        "warnings": [],
    }


def _find(text, labels):
    lines = [line.strip() for line in text.splitlines()]
    for label in sorted(labels, key=len, reverse=True):
        pattern = re.compile(
            r"^\s*" + re.escape(label) + r"\s*(?:(?:[:|#-])\s*|\s+)(.+?)\s*$",
            re.I,
        )
        for index, line in enumerate(lines):
            match = pattern.match(line)
            if match and match.group(1).strip():
                return match.group(1).strip(), line
            if line.casefold().rstrip(":") == label.casefold():
                for following in lines[index + 1:]:
                    if following:
                        return following, line + " | " + following
    return None, None


def _decimal(value):
    if value is None:
        return None
    candidate = re.sub(r"[^\d,.\-]", "", str(value)).replace(",", "")
    try:
        return Decimal(candidate)
    except (InvalidOperation, ValueError):
        return None


def _extract_phone(text, pages):
    lines = text.splitlines()
    # Prefer an explicitly labelled contact line.
    for line in lines:
        low = line.lower()
        if any(token in low for token in PHONE_SKIP):
            continue
        if re.search(r"\b(phone|mobile|contact|telephone|tel)\b", low):
            match = re.search(PHONE, line)
            if match:
                return _field(match.group(0), line.strip(), pages, "labelled_phone_pattern")
    # Unlabelled fallback only accepts a complete 10-digit Indian mobile or +91 number.
    for line in lines:
        low = line.lower()
        if any(token in low for token in PHONE_SKIP):
            continue
        match = re.search(PHONE, line)
        if match:
            return _field(match.group(0), line.strip(), pages, "indian_phone_pattern")
    return None


def _extract_gstins(text, pages, fields):
    matches = list(re.finditer(GSTIN, text, re.I))
    if not matches:
        return
    bill_to = re.search(r"\bbill\s+to\b", text, re.I)
    for match in matches:
        value = match.group(0).upper()
        before_bill_to = bill_to is None or match.start() < bill_to.start()
        key = "vendor_gstin" if before_bill_to else "customer_gstin"
        if key not in fields:
            line = next((line.strip() for line in text.splitlines() if value in line.upper()), value)
            fields[key] = _field(value, line, pages, "gstin_pattern")


def _extract_invoice_parties(text, pages, fields):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    upper = text.upper()
    if "vendor_name" not in fields:
        # In conventional invoices the supplier identity is the first heading before TAX INVOICE.
        marker = re.search(r"\bTAX\s+INVOICE\b|\bINVOICE\b", upper)
        prefix = text[:marker.start()] if marker else ""
        candidates = [line for line in prefix.splitlines() if line.strip()]
        if candidates:
            value = candidates[0].strip()
            if len(value) <= 120 and not re.search(r"GSTIN|^\d", value, re.I):
                fields["vendor_name"] = _field(value, value, pages, "invoice_header")
    if "customer_name" not in fields:
        match = re.search(r"\bBILL\s+TO\b", upper)
        if match:
            remainder = text[match.end():]
            for line in remainder.splitlines():
                candidate = line.strip()
                if candidate and not re.search(r"GSTIN|EMAIL|PHONE|^\d", candidate, re.I):
                    fields["customer_name"] = _field(candidate, candidate, pages, "bill_to_block")
                    break


def _extract_line_items(tables, pages):
    items = []
    for table in tables or []:
        rows = table.get("rows") or []
        if len(rows) < 2:
            continue
        header_index = next(
            (i for i, row in enumerate(rows[:3])
             if any("description" in str(cell).lower() or "particular" in str(cell).lower() for cell in row)
             and any("amount" in str(cell).lower() for cell in row)),
            None,
        )
        if header_index is None:
            continue
        headers = [re.sub(r"[^a-z]", "", str(cell).lower()) for cell in rows[header_index]]
        def column(*tokens):
            return next((i for i, header in enumerate(headers) if any(token in header for token in tokens)), None)
        desc_i = column("description", "particular", "item")
        hsn_i = column("hsnsac", "hsn", "sac")
        qty_i = column("qty", "quantity")
        price_i = column("unitprice", "rate", "price")
        amount_i = column("amount", "total")
        for row in rows[header_index + 1:]:
            if not row or desc_i is None or amount_i is None:
                continue
            description = str(row[desc_i]).strip() if desc_i < len(row) else ""
            amount_raw = str(row[amount_i]).strip() if amount_i < len(row) else ""
            if not description or not amount_raw or _decimal(amount_raw) is None:
                continue
            item = {
                "description": description,
                "hsn_sac": str(row[hsn_i]).strip() if hsn_i is not None and hsn_i < len(row) else None,
                "quantity": str(row[qty_i]).strip() if qty_i is not None and qty_i < len(row) else None,
                "unit_price": str(row[price_i]).strip() if price_i is not None and price_i < len(row) else None,
                "amount": amount_raw,
                "normalized_unit_price": normalize_value("unit_price", str(row[price_i])) if price_i is not None and price_i < len(row) else None,
                "normalized_amount": normalize_value("line_amount", amount_raw),
            }
            items.append(item)
    if not items:
        return None
    page = tables[0].get("page") if tables else None
    return {
        "value": items,
        "normalized_value": None,
        "confidence": None,
        "source": {"page": page, "text": "Extracted from document table", "method": "table_header_mapping", "bounding_box": None},
        "validation_status": "not_checked",
        "warnings": [],
    }


def extract_fields(text, document_type, pages, tables=None):
    schema = SCHEMAS.get(document_type, SCHEMAS["general_document"])
    fields = {}
    for key, labels in schema["fields"].items():
        value, evidence = _find(text, labels)
        if value:
            fields[key] = _field(value, evidence, pages)

    if document_type == "invoice":
        _extract_invoice_parties(text, pages, fields)
        _extract_gstins(text, pages, fields)
        # GSTINs can be printed on a separate line without an explicit label.
        currency_match = re.search(r"\b(INR|USD|EUR|GBP|AED)\b|₹|€|£|\$", text, re.I)
        if currency_match and "currency" not in fields:
            token = currency_match.group(0)
            currency = {"₹": "INR", "€": "EUR", "£": "GBP", "$": "USD"}.get(token, token.upper())
            fields["currency"] = _field(currency, currency_match.group(0), pages, "currency_pattern")
        if "grand_total" in fields and "total_amount" not in fields:
            fields["total_amount"] = dict(fields["grand_total"])
        elif "total_amount" in fields and "grand_total" not in fields:
            fields["grand_total"] = dict(fields["total_amount"])
        line_items = _extract_line_items(tables, pages)
        if line_items:
            fields["line_items"] = line_items

    if "email" not in fields:
        match = re.search(EMAIL, text, re.I)
        if match:
            fields["email"] = _field(match.group(0), match.group(0), pages, "email_pattern")
    if "phone" not in fields:
        phone_field = _extract_phone(text, pages)
        if phone_field:
            fields["phone"] = phone_field

    return normalize_fields(fields)


def validate_fields(fields, document_type):
    schema = SCHEMAS.get(document_type, SCHEMAS["general_document"])
    errors, warnings = [], []
    for key in schema["required"]:
        if key not in fields:
            errors.append({"field": key, "code": "required_missing", "message": f"Required field '{key}' was not found."})

    for key, item in fields.items():
        value = str(item.get("value", ""))
        if key == "email" and not re.fullmatch(EMAIL, value, re.I):
            errors.append({"field": key, "code": "invalid_format", "message": "Email format is invalid."})
        if key == "phone" and item.get("normalized_value") is None:
            warnings.append({"field": key, "code": "phone_unrecognized", "message": "Phone number could not be normalized as a supported phone number."})
        if key in DATE_FIELDS and item.get("normalized_value") is None:
            warnings.append({"field": key, "code": "date_unrecognized", "message": "Date could not be normalized unambiguously."})
        if key in AMOUNT_FIELDS and item.get("normalized_value") is None:
            warnings.append({"field": key, "code": "amount_unrecognized", "message": "Amount could not be normalized."})

    line_items = fields.get("line_items", {}).get("value", [])
    subtotal = _decimal(fields.get("subtotal", {}).get("normalized_value") or fields.get("subtotal", {}).get("value"))
    if line_items and subtotal is not None:
        line_sum = sum((_decimal(item.get("normalized_amount") or item.get("amount")) or Decimal("0") for item in line_items), Decimal("0"))
        if abs(line_sum - subtotal) > Decimal("0.01"):
            warnings.append({
                "field": "subtotal", "code": "line_items_subtotal_mismatch",
                "message": f"Line-item sum ({line_sum:.2f}) does not match subtotal ({subtotal:.2f}).",
            })

    tax_keys = ("cgst_amount", "sgst_amount", "igst_amount")
    tax_values = [_decimal(fields.get(key, {}).get("normalized_value") or fields.get(key, {}).get("value")) for key in tax_keys]
    present_taxes = [value for value in tax_values if value is not None]
    total_tax = _decimal(fields.get("total_tax", {}).get("normalized_value") or fields.get("total_tax", {}).get("value"))
    if present_taxes and total_tax is not None:
        calculated_tax = sum(present_taxes, Decimal("0"))
        if abs(calculated_tax - total_tax) > Decimal("0.01"):
            warnings.append({
                "field": "total_tax", "code": "tax_components_mismatch",
                "message": f"Tax components ({calculated_tax:.2f}) do not match total tax ({total_tax:.2f}).",
            })
    elif present_taxes and total_tax is None:
        total_tax = sum(present_taxes, Decimal("0"))

    grand_total = _decimal(fields.get("grand_total", {}).get("normalized_value") or fields.get("grand_total", {}).get("value"))
    if subtotal is not None and grand_total is not None and total_tax is not None:
        expected_total = subtotal + total_tax
        if abs(expected_total - grand_total) > Decimal("0.01"):
            warnings.append({
                "field": "grand_total", "code": "grand_total_mismatch",
                "message": f"Subtotal plus tax ({expected_total:.2f}) does not match grand total ({grand_total:.2f}).",
            })

    for key, item in fields.items():
        item["validation_status"] = (
            "invalid" if any(error["field"] == key for error in errors)
            else "warning" if any(warning["field"] == key for warning in warnings)
            else "valid"
        )
    return {"is_valid": not errors, "errors": errors, "warnings": warnings}
