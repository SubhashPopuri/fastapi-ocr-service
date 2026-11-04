"""Schema-guided extraction with source evidence and conservative validation."""
import re
from decimal import Decimal, InvalidOperation

from .schemas import SCHEMAS
from .normalization import normalize_fields, normalize_value

EMAIL = r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"
PHONE = r"(?<!\d)(?:(?:\+?91)[\s().-]*)?[6-9](?:[\s().-]*\d){9}(?!\d)"
GSTIN = r"(?<![A-Z0-9])[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z](?![A-Z0-9])"
PAN = r"(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])"
PAN_HOLDER_TYPES = {
    "P": "individual", "C": "company", "H": "hindu_undivided_family",
    "A": "association_of_persons", "B": "body_of_individuals", "G": "government_agency",
    "J": "artificial_juridical_person", "L": "local_authority", "F": "firm_or_llp", "T": "trust",
}
DATE_FIELDS = {"invoice_date", "due_date", "po_date", "effective_date", "expiry_date", "document_date", "date_of_birth"}
AMOUNT_FIELDS = {
    "total_amount", "tax_amount", "subtotal", "cgst_amount", "sgst_amount",
    "igst_amount", "total_tax", "grand_total", "amount_due", "unit_price",
    "line_amount", "net_pay", "gross_pay", "deductions", "opening_balance", "closing_balance",
}
PHONE_SKIP = ("invoice", "gstin", "hsn", "sac", "ifsc", "account number", "due date", "invoice date")


def _field(value, evidence, pages, method="label_pattern"):
    page = next(
        (p["page"] for p in pages
         if evidence in p.get("text", "") or str(value) in p.get("text", "")),
        None,
    )
    return {
        "value": value, "normalized_value": None, "confidence": None,
        "source": {"page": page, "text": evidence[:300], "method": method, "bounding_box": None},
        "validation_status": "not_checked", "warnings": [],
    }


def _find(text, labels):
    lines = [line.strip() for line in text.splitlines()]
    for label in sorted(labels, key=len, reverse=True):
        pattern = re.compile(r"^\s*" + re.escape(label) + r"\s*(?:(?:[:|#-])\s*|\s+)(.+?)\s*$", re.I)
        for index, line in enumerate(lines):
            match = pattern.match(line)
            if match and match.group(1).strip():
                return match.group(1).strip(), line
            if line.casefold().rstrip(":") == label.casefold():
                for following in lines[index + 1:]:
                    if following:
                        return following, line + " | " + following
    return None, None


def _clean_amount(value):
    if value is None:
        return None
    raw = re.sub(r"\(\s*\d+(?:\.\d+)?\s*%\s*\)", " ", str(value).strip())
    candidates = re.findall(r"(?<![A-Za-z0-9])[-+]?\d[\d,]*(?:\.\d{1,})?", raw)
    return candidates[-1] if candidates else None


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
    for line in lines:
        low = line.lower()
        if any(token in low for token in PHONE_SKIP):
            continue
        if re.search(r"\b(phone|mobile|contact|telephone|tel)\b", low):
            match = re.search(PHONE, line)
            if match:
                return _field(match.group(0), line.strip(), pages, "labelled_phone_pattern")
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
        key = "vendor_gstin" if bill_to is None or match.start() < bill_to.start() else "customer_gstin"
        if key not in fields:
            line = next((line.strip() for line in text.splitlines() if value in line.upper()), value)
            fields[key] = _field(value, line, pages, "gstin_pattern")


def _extract_invoice_parties(text, pages, fields):
    upper = text.upper()
    if "vendor_name" not in fields:
        marker = re.search(r"\bTAX\s+INVOICE\b|\bINVOICE\b", upper)
        candidates = [line for line in text[:marker.start()].splitlines() if line.strip()] if marker else []
        if candidates:
            value = candidates[0].strip()
            if len(value) <= 120 and not re.search(r"GSTIN|^\d", value, re.I):
                fields["vendor_name"] = _field(value, value, pages, "invoice_header")
    if "customer_name" not in fields:
        match = re.search(r"\bBILL\s+TO\b", upper)
        if match:
            for line in text[match.end():].splitlines():
                candidate = line.strip()
                if candidate and not re.search(r"GSTIN|EMAIL|PHONE|^\d", candidate, re.I):
                    fields["customer_name"] = _field(candidate, candidate, pages, "bill_to_block")
                    break


def _clean_pan_name_candidate(value):
    """Remove obvious OCR spillover from uppercase PAN-card name lines.

    Printed PAN holder names are commonly uppercase. When two or more
    uppercase name tokens are followed by mixed/lowercase OCR fragments,
    retain the uppercase name portion rather than treating the fragments
    as additional name tokens. Title-case names without this pattern remain
    unchanged.
    """
    tokens = str(value).split()
    if len(tokens) < 3:
        return str(value).strip()

    uppercase_prefix = 0
    for token in tokens:
        if re.fullmatch(r"[A-Z][A-Z.'-]*", token):
            uppercase_prefix += 1
        else:
            break

    if uppercase_prefix >= 2 and uppercase_prefix < len(tokens):
        return " ".join(tokens[:uppercase_prefix]).strip()
    return str(value).strip()


def _extract_pan_fields(text, pages, fields):
    if "pan_number" not in fields:
        match = re.search(PAN, text, re.I)
        if match:
            fields["pan_number"] = _field(match.group(0).upper(), match.group(0), pages, "pan_pattern")
    if "pan_number" in fields:
        candidate = re.sub(r"[\s-]", "", str(fields["pan_number"]["value"])).upper()
        fields["pan_number"]["value"] = candidate
        if len(candidate) == 10 and candidate[3] in PAN_HOLDER_TYPES:
            fields["holder_category"] = _field(PAN_HOLDER_TYPES[candidate[3]], candidate, pages, "pan_structure")
    # PAN cards commonly print the name and parent name as standalone lines after their labels.
    if "full_name" not in fields:
        name, evidence = _find(text, ["name of holder", "cardholder name", "name"])
        if name:
            fields["full_name"] = _field(name, evidence, pages, "pan_label")
    if "parent_name" not in fields:
        parent, evidence = _find(text, ["father's name", "father name", "mother's name", "mother name", "parent name"])
        if parent:
            fields["parent_name"] = _field(parent, evidence, pages, "pan_label")
    if "date_of_birth" not in fields:
        dob, evidence = _find(text, ["date of birth", "dob"])
        if dob:
            fields["date_of_birth"] = _field(dob, evidence, pages, "pan_label")
    if "gender" not in fields:
        gender, evidence = _find(text, ["gender", "sex"])
        if gender:
            normalized = normalize_value("gender", gender)
            if normalized:
                fields["gender"] = _field(gender, evidence, pages, "pan_label")

    # Many physical PAN cards have no printed labels beside the holder and
    # parent names. OCR therefore returns two name lines followed by a
    # standalone DOB. Use this conservative layout fallback only when labels
    # did not yield the corresponding fields.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    dob_pattern = re.compile(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})$")
    dob_index = next((i for i, line in enumerate(lines) if dob_pattern.fullmatch(line)), None)
    if dob_index is not None:
        dob_line = lines[dob_index]
        if "date_of_birth" not in fields:
            fields["date_of_birth"] = _field(dob_line, dob_line, pages, "pan_layout_dob")
        if "full_name" not in fields or "parent_name" not in fields:
            excluded = re.compile(
                r"\b(income tax|department|government|govt|india|permanent|account|number|"
                r"signature|sample|imm[i1]help)\b", re.I
            )
            name_candidates = [
                (i, line) for i, line in enumerate(lines[:dob_index])
                if len(line) <= 100
                and re.fullmatch(r"[A-Za-z][A-Za-z .'-]{2,}", line)
                and len(line.split()) >= 2
                and not excluded.search(line)
            ]
            # Clean OCR spillover before assigning layout-derived names. Keep
            # the original line as source evidence so reviewers can audit it.
            cleaned_candidates = [
                (index, line, _clean_pan_name_candidate(line))
                for index, line in name_candidates
            ]
            if "full_name" not in fields and cleaned_candidates:
                index, evidence, value = cleaned_candidates[-2] if len(cleaned_candidates) >= 2 else cleaned_candidates[-1]
                fields["full_name"] = _field(value, evidence, pages, "pan_layout_name")
            if "parent_name" not in fields and len(cleaned_candidates) >= 2:
                index, evidence, value = cleaned_candidates[-1]
                if "full_name" not in fields or value != fields["full_name"]["value"]:
                    fields["parent_name"] = _field(value, evidence, pages, "pan_layout_parent_name")


def _extract_line_items(tables, pages):
    items = []
    for table in tables or []:
        rows = table.get("rows") or []
        if len(rows) < 2:
            continue
        header_index = next((i for i, row in enumerate(rows[:3])
            if any("description" in str(cell).lower() or "particular" in str(cell).lower() for cell in row)
            and any("amount" in str(cell).lower() for cell in row)), None)
        if header_index is None:
            continue
        headers = [re.sub(r"[^a-z]", "", str(cell).lower()) for cell in rows[header_index]]
        def column(*tokens):
            return next((i for i, header in enumerate(headers) if any(token in header for token in tokens)), None)
        desc_i, hsn_i, qty_i = column("description", "particular", "item"), column("hsnsac", "hsn", "sac"), column("qty", "quantity")
        price_i, amount_i = column("unitprice", "rate", "price"), column("amount", "total")
        for row in rows[header_index + 1:]:
            if not row or desc_i is None or amount_i is None:
                continue
            description = str(row[desc_i]).strip() if desc_i < len(row) else ""
            amount_raw = str(row[amount_i]).strip() if amount_i < len(row) else ""
            if not description or not amount_raw or _decimal(amount_raw) is None:
                continue
            items.append({
                "description": description,
                "hsn_sac": str(row[hsn_i]).strip() if hsn_i is not None and hsn_i < len(row) else None,
                "quantity": str(row[qty_i]).strip() if qty_i is not None and qty_i < len(row) else None,
                "unit_price": str(row[price_i]).strip() if price_i is not None and price_i < len(row) else None,
                "amount": amount_raw,
                "normalized_unit_price": normalize_value("unit_price", str(row[price_i])) if price_i is not None and price_i < len(row) else None,
                "normalized_amount": normalize_value("line_amount", amount_raw),
            })
    if not items:
        return None
    return {"value": items, "normalized_value": None, "confidence": None,
            "source": {"page": tables[0].get("page"), "text": "Extracted from document table",
                       "method": "table_header_mapping", "bounding_box": None},
            "validation_status": "not_checked", "warnings": []}


def extract_fields(text, document_type, pages, tables=None):
    schema = SCHEMAS.get(document_type, SCHEMAS["general_document"])
    fields = {}
    for key, labels in schema["fields"].items():
        # PAN numbers must be extracted with the strict 10-character pattern below.
        # Generic label matching can mistake "CARD" in the heading for the PAN value.
        if document_type == "pan_card" and key == "pan_number":
            continue
        value, evidence = _find(text, labels)
        if value:
            if key in AMOUNT_FIELDS:
                value = _clean_amount(value) or value
            fields[key] = _field(value, evidence, pages)

    if document_type == "invoice":
        _extract_invoice_parties(text, pages, fields)
        _extract_gstins(text, pages, fields)
        currency_match = re.search(r"\b(INR|USD|EUR|GBP|AED)\b|₹|€|£|\$", text, re.I)
        if currency_match and "currency" not in fields:
            token = currency_match.group(0)
            currency = {"₹": "INR", "€": "EUR", "£": "GBP", "$": "USD"}.get(token, token.upper())
            fields["currency"] = _field(currency, token, pages, "currency_pattern")
        if "grand_total" in fields and "total_amount" not in fields:
            fields["total_amount"] = dict(fields["grand_total"])
        elif "total_amount" in fields and "grand_total" not in fields:
            fields["grand_total"] = dict(fields["total_amount"])
        line_items = _extract_line_items(tables, pages)
        if line_items:
            fields["line_items"] = line_items

    if document_type == "pan_card":
        _extract_pan_fields(text, pages, fields)

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
        if key == "pan_number":
            if not re.fullmatch(PAN, value, re.I):
                errors.append({"field": key, "code": "pan_invalid_format", "message": "PAN must match the 10-character format AAAAA9999A."})
            elif value[3].upper() not in PAN_HOLDER_TYPES:
                errors.append({"field": key, "code": "pan_invalid_holder_type", "message": "The fourth PAN character is not a recognized holder category."})
        if key == "date_of_birth" and item.get("normalized_value") is None:
            warnings.append({"field": key, "code": "date_unrecognized", "message": "Date of birth could not be normalized unambiguously."})
        if key == "phone" and item.get("normalized_value") is None:
            warnings.append({"field": key, "code": "phone_unrecognized", "message": "Phone number could not be normalized as a supported phone number."})
        if key in DATE_FIELDS - {"date_of_birth"} and item.get("normalized_value") is None:
            warnings.append({"field": key, "code": "date_unrecognized", "message": "Date could not be normalized unambiguously."})
        if key in AMOUNT_FIELDS and item.get("normalized_value") is None:
            warnings.append({"field": key, "code": "amount_unrecognized", "message": "Amount could not be normalized."})

    line_items = fields.get("line_items", {}).get("value", [])
    subtotal = _decimal(fields.get("subtotal", {}).get("normalized_value") or fields.get("subtotal", {}).get("value"))
    if line_items and subtotal is not None:
        line_sum = sum((_decimal(item.get("normalized_amount") or item.get("amount")) or Decimal("0") for item in line_items), Decimal("0"))
        if abs(line_sum - subtotal) > Decimal("0.01"):
            warnings.append({"field": "subtotal", "code": "line_items_subtotal_mismatch",
                "message": f"Line-item sum ({line_sum:.2f}) does not match subtotal ({subtotal:.2f})."})
    tax_keys = ("cgst_amount", "sgst_amount", "igst_amount")
    tax_values = [_decimal(fields.get(key, {}).get("normalized_value") or fields.get(key, {}).get("value")) for key in tax_keys]
    present_taxes = [value for value in tax_values if value is not None]
    total_tax = _decimal(fields.get("total_tax", {}).get("normalized_value") or fields.get("total_tax", {}).get("value"))
    if present_taxes and total_tax is not None:
        calculated_tax = sum(present_taxes, Decimal("0"))
        if abs(calculated_tax - total_tax) > Decimal("0.01"):
            warnings.append({"field": "total_tax", "code": "tax_components_mismatch",
                "message": f"Tax components ({calculated_tax:.2f}) do not match total tax ({total_tax:.2f})."})
    elif present_taxes and total_tax is None:
        total_tax = sum(present_taxes, Decimal("0"))
    grand_total = _decimal(fields.get("grand_total", {}).get("normalized_value") or fields.get("grand_total", {}).get("value"))
    if subtotal is not None and grand_total is not None and total_tax is not None:
        expected_total = subtotal + total_tax
        if abs(expected_total - grand_total) > Decimal("0.01"):
            warnings.append({"field": "grand_total", "code": "grand_total_mismatch",
                "message": f"Subtotal plus tax ({expected_total:.2f}) does not match grand total ({grand_total:.2f})."})
    for key, item in fields.items():
        item["validation_status"] = (
            "invalid" if any(error["field"] == key for error in errors)
            else "warning" if any(warning["field"] == key for warning in warnings)
            else "valid"
        )
    return {"is_valid": not errors, "errors": errors, "warnings": warnings}
