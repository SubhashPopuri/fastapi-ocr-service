from fastapi.testclient import TestClient
from docintel.classification import classify
from docintel.extraction import extract_fields,validate_fields
from docintel.normalization import normalize_value
from docintel.pipeline import process_document

def test_invoice_classification():
    result=classify("TAX INVOICE Invoice Number: INV-1 Amount Due: 100")
    assert result["document_type"]=="invoice" and result["confidence"] is None

def test_schema_extraction_and_validation():
    text="Invoice Number: INV-100\nInvoice Date: 2026-11-04\nTotal Amount: INR 1,250.00"
    fields=extract_fields(text,"invoice",[{"page":1,"text":text}])
    assert fields["invoice_number"]["value"]=="INV-100"
    assert fields["total_amount"]["normalized_value"]=="1250.00"
    assert validate_fields(fields,"invoice")["is_valid"]

def test_ambiguous_date_not_guessed():
    assert normalize_value("invoice_date","01/02/2025") is None

def test_unknown_fallback():
    assert classify("A page containing unlabelled prose")["document_type"]=="general_document"

def test_text_pipeline_raw_text_is_opt_in_and_page_text_is_private():
    result=process_document("invoice.txt",b"Invoice Number: INV-200\nInvoice Date: 2026-11-04\nTotal Amount: 200","text/plain")
    assert result["document"]["document_type"]=="invoice"
    assert result["extracted_data"]["invoice_number"]["value"]=="INV-200"
    assert result["extracted_data"]["total_amount"]["normalized_value"]=="200.00"
    assert "raw_text" not in result
    assert "text" not in result["pages"][0]
    full=process_document("invoice.txt",b"Invoice Number: INV-200","text/plain",True)
    assert full["raw_text"]=="Invoice Number: INV-200"

def test_http_api_accepts_text_document():
    from main import app
    client=TestClient(app)
    response=client.post("/v1/documents/process",files={"file":("invoice.txt",b"Invoice Number: API-300\nInvoice Date: 2026-11-04","text/plain")})
    assert response.status_code==200
    body=response.json()
    assert body["extracted_data"]["invoice_number"]["value"]=="API-300"
    assert "raw_text" not in body

def test_main_registers_legacy_and_v1_routes():
    from main import app
    paths={route.path for route in app.routes}
    assert "/pdf" in paths and "/image" in paths
    assert "/v1/documents/process" in paths and "/v1/documents/schemas" in paths

def test_json_file_is_flattened_for_schema_extraction():
    result=process_document("invoice.json",b'{"invoice_number":"JSON-42","invoice_date":"2026-11-04"}',"application/json")
    assert result["document"]["document_type"]=="invoice"
    assert result["extracted_data"]["invoice_number"]["value"]=="JSON-42"


def test_month_name_invoice_date_normalizes():
    assert normalize_value("invoice_date", "04-Nov-2026") == "2026-11-04"
    assert normalize_value("due_date", "19-Nov-2026") == "2026-11-19"


def test_phone_extraction_does_not_capture_invoice_number():
    text = "Invoice No: INV-2026-1042\nPhone: +91 98765 43210"
    fields = extract_fields(text, "invoice", [{"page": 1, "text": text}])
    assert fields["phone"]["value"] == "+91 98765 43210"
    assert fields["phone"]["normalized_value"] == "+919876543210"


def test_invoice_party_gstin_and_currency_extraction():
    text = (
        "ACME OFFICE SUPPLIES\nTAX INVOICE\nInvoice No: INV-2026-1042\n"
        "GSTIN: 36ABCDE1234F1Z5\nBILL TO\nDemo Customer Private Limited\n"
        "GSTIN: 36AABCD1234E1Z2\nEmail: accounts@example.com"
    )
    fields = extract_fields(text, "invoice", [{"page": 1, "text": text}])
    assert fields["vendor_name"]["value"] == "ACME OFFICE SUPPLIES"
    assert fields["customer_name"]["value"] == "Demo Customer Private Limited"
    assert fields["vendor_gstin"]["value"] == "36ABCDE1234F1Z5"
    assert fields["customer_gstin"]["value"] == "36AABCD1234E1Z2"


def test_invoice_line_items_and_financial_reconciliation():
    text = (
        "Invoice Number: INV-TEST-1\nSubtotal: INR 105,000.00\n"
        "CGST: INR 9,450.00\nSGST: INR 9,450.00\n"
        "Grand Total: INR 123,900.00\nAmount Due: INR 123,900.00"
    )
    tables = [{
        "page": 1, "table_index": 1,
        "rows": [
            ["Description", "HSN/SAC", "Qty", "Unit Price (INR)", "Amount (INR)"],
            ["Office laptops", "84713010", "2", "45,000.00", "90,000.00"],
            ["Wireless keyboards", "84716040", "5", "1,200.00", "6,000.00"],
            ["USB-C docking stations", "84718000", "2", "4,500.00", "9,000.00"],
        ],
    }]
    fields = extract_fields(text, "invoice", [{"page": 1, "text": text}], tables)
    validation = validate_fields(fields, "invoice")
    assert len(fields["line_items"]["value"]) == 3
    assert fields["subtotal"]["normalized_value"] == "105000.00"
    assert fields["grand_total"]["normalized_value"] == "123900.00"
    assert not any(w["code"] == "line_items_subtotal_mismatch" for w in validation["warnings"])
    assert not any(w["code"] == "grand_total_mismatch" for w in validation["warnings"])


def test_financial_reconciliation_flags_mismatch():
    fields = {
        "subtotal": {"value": "100", "normalized_value": "100.00"},
        "cgst_amount": {"value": "9", "normalized_value": "9.00"},
        "sgst_amount": {"value": "9", "normalized_value": "9.00"},
        "grand_total": {"value": "120", "normalized_value": "120.00"},
    }
    validation = validate_fields(fields, "invoice")
    assert any(w["code"] == "grand_total_mismatch" for w in validation["warnings"])


def test_tax_rate_percentage_is_not_included_in_tax_amount():
    text = (
        "Invoice Number: INV-2026-1042\n"
        "Subtotal: INR 105,000.00\n"
        "CGST (9%) INR 9,450.00\n"
        "SGST (9%) INR 9,450.00\n"
        "Grand Total: INR 123,900.00"
    )
    fields = extract_fields(text, "invoice", [{"page": 1, "text": text}])
    assert fields["cgst_amount"]["value"] == "9,450.00"
    assert fields["cgst_amount"]["normalized_value"] == "9450.00"
    assert fields["sgst_amount"]["normalized_value"] == "9450.00"
    validation = validate_fields(fields, "invoice")
    assert not any(w["code"] == "grand_total_mismatch" for w in validation["warnings"])


def test_bill_to_block_source_page_is_resolved():
    text = "TAX INVOICE\nInvoice Number: INV-2\nBILL TO\nDemo Customer Private Limited"
    fields = extract_fields(text, "invoice", [{"page": 1, "text": text}])
    assert fields["customer_name"]["source"]["page"] == 1
