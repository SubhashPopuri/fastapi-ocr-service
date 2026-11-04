"""Explainable keyword classifier; rule strength is not a probability."""
import re
RULES={"invoice":["invoice","tax invoice","invoice number","amount due","bill to"],"purchase_order":["purchase order","po number","order quantity","ship to"],"employee_id":["employee id","employee name","staff id","identity card"],"resume":["curriculum vitae","professional summary","work experience","technical skills"],"payslip":["payslip","pay slip","net pay","gross salary","salary statement"],"bank_statement":["bank statement","opening balance","closing balance","transaction date"],"contract":["agreement","contract","terms and conditions","effective date"]}
def classify(text):
    normalized=re.sub(r"\s+"," ",text.lower())
    ranked=sorted(((k,[term for term in terms if term in normalized]) for k,terms in RULES.items()),key=lambda item:len(item[1]),reverse=True)
    best,evidence=ranked[0]; count=len(evidence); second=len(ranked[1][1])
    if count==0: return {"document_type":"general_document","method":"keyword_rules","confidence":None,"rule_strength":None,"evidence":[],"review_required":True}
    ambiguous=count==second
    return {"document_type":best if not ambiguous else "general_document","method":"keyword_rules","confidence":None,"rule_strength":round(min(1.0,count/4),2),"evidence":evidence,"review_required":ambiguous or count<2}
