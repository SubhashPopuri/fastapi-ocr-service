# Workday integration boundary

The document engine returns canonical extracted fields. The Workday adapter maps only explicitly configured canonical field names to tenant-specific target field names. It creates an idempotency key and a prepared payload. The included mock adapter simulates acceptance and never contacts a Workday tenant.

No Workday API endpoint, authentication scheme, business object, tenant configuration or write operation is assumed. A live connector must be implemented only after the tenant's approved API contract, OAuth/client credentials, security scope and target business process are supplied. Human approval and authorization should gate any write.
