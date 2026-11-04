"""Versioned, declarative document type schemas."""
SCHEMAS={
"invoice":{"version":"1.0","required":["invoice_number"],"fields":{"invoice_number":["invoice number","invoice no","bill number"],"invoice_date":["invoice date","date"],"due_date":["due date"],"vendor_name":["vendor","supplier","seller"],"customer_name":["bill to","customer"],"total_amount":["grand total","total amount","amount due","total"],"tax_amount":["tax amount","gst","vat"],"currency":["currency"]}},
"purchase_order":{"version":"1.0","required":["po_number"],"fields":{"po_number":["po number","purchase order","order number"],"po_date":["order date","po date"],"vendor_name":["vendor","supplier"],"total_amount":["total","order total"]}},
"employee_id":{"version":"1.0","required":["person_name"],"fields":{"person_name":["employee name","name"],"employee_id":["employee id","staff id"],"department":["department"],"designation":["designation","job title"],"email":["email","e-mail"]}},
"resume":{"version":"1.0","required":[],"fields":{"person_name":["candidate name","name"],"email":["email","e-mail"],"phone":["phone","mobile"],"skills":["skills","technical skills"],"experience":["experience","work experience"],"education":["education","qualification"]}},
"payslip":{"version":"1.0","required":["net_pay"],"fields":{"employee_name":["employee name","name"],"employee_id":["employee id","employee code"],"pay_period":["pay period","salary month"],"gross_pay":["gross pay","gross salary"],"net_pay":["net pay","take home","net salary"],"deductions":["deductions","total deductions"]}},
"bank_statement":{"version":"1.0","required":[],"fields":{"account_holder":["account holder","customer name"],"account_number":["account number","a/c no"],"statement_period":["statement period"],"opening_balance":["opening balance"],"closing_balance":["closing balance"]}},
"contract":{"version":"1.0","required":[],"fields":{"contract_number":["contract number","agreement number"],"effective_date":["effective date","commencement date"],"expiry_date":["expiry date","end date"],"party_name":["between","party"]}},
"general_document":{"version":"1.0","required":[],"fields":{"title":["title","subject"],"document_date":["document date","date"]}}}
def list_schemas():
    return [{"document_type":k,"version":v["version"],"required_fields":v["required"],"fields":list(v["fields"])} for k,v in SCHEMAS.items()]
