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
