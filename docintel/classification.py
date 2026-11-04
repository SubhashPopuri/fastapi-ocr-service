"""Explainable keyword classifier; rule strength is not a probability."""
import re

RULES = {
    "pan_card": ["permanent account number", "pan card", "income tax department", "father's name"],
    "invoice": ["invoice", "tax invoice", "invoice number", "amount due", "bill to"],
    "purchase_order": ["purchase order", "po number", "order quantity", "ship to"],
    "employee_id": ["employee id", "employee name", "staff id", "identity card"],
    "resume": ["curriculum vitae", "professional summary", "work experience", "technical skills"],
    "payslip": ["payslip", "pay slip", "net pay", "gross salary", "salary statement"],
    "bank_statement": ["bank statement", "opening balance", "closing balance", "transaction date"],
    "contract": ["agreement", "contract", "terms and conditions", "effective date"],
}

PAN_PATTERN = re.compile(r"(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])", re.I)


def classify(text):
    normalized = re.sub(r"\s+", " ", text.lower())
    ranked = sorted(
        ((key, [term for term in terms if term in normalized]) for key, terms in RULES.items()),
        key=lambda item: len(item[1]), reverse=True,
    )
    best, evidence = ranked[0]
    count = len(evidence)
    second = len(ranked[1][1])
    # A PAN-shaped identifier plus a PAN-specific label is stronger evidence than generic keywords.
    has_pan_number = bool(PAN_PATTERN.search(text))
    has_pan_context = any(term in normalized for term in ("pan", "permanent account number", "income tax department"))
    if has_pan_number and has_pan_context:
        evidence = list(dict.fromkeys(evidence + ["pan_number_pattern"]))
        count = len(evidence)
        best = "pan_card"
        second = max((len(matches) for key, matches in ranked if key != "pan_card"), default=0)
    if count == 0:
        return {"document_type": "general_document", "method": "keyword_rules", "confidence": None,
                "rule_strength": None, "evidence": [], "review_required": True}
    ambiguous = count == second
    return {"document_type": best if not ambiguous else "general_document", "method": "keyword_rules",
            "confidence": None, "rule_strength": round(min(1.0, count / 4), 2),
            "evidence": evidence, "review_required": ambiguous or count < 2}
