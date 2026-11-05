# Document Intelligence Demo Web App

A single-user demonstration portal served by the existing FastAPI application. The browser never receives the OCR API key: the portal authenticates the user with a password-backed signed session cookie and proxies file uploads server-to-server to the existing versioned OCR endpoint.

## Architecture

```text
Browser
  | HTTPS + signed HttpOnly session cookie
  v
FastAPI demo portal (/app)
  | server-side multipart request + X-API-Key
  v
Document Intelligence API (/v1/documents/process)
  | Tesseract / document pipeline
  v
Structured JSON response -> browser result view
```

The demo portal is mounted in the existing API service. It is not a separate frontend deployment and does not duplicate the OCR pipeline.

## Routes

- `GET /app` — demo UI and password login screen
- `POST /app/login` — create an eight-hour signed session
- `POST /app/logout` — clear the session
- `GET /app/api/status` — authenticated upstream API connectivity check
- `POST /app/api/process` — authenticated file upload proxy
- `POST /v1/documents/process` — existing OCR API (API-key protected)

## Render environment variables

Configure these in the Render service environment. Never put secrets in frontend JavaScript or source control.

| Variable | Purpose |
|---|---|
| `DOCINTEL_API_KEY` | Existing API key used by the OCR endpoint |
| `DOCINTEL_DEMO_PASSWORD` | Password for the single-user demo portal |
| `DOCINTEL_DEMO_SESSION_SECRET` | Long random secret used to sign session cookies |
| `DOCINTEL_UPSTREAM_API_URL` | Base URL of the OCR API service |

The Render blueprint generates values for the API key, demo password and session secret, and sets the upstream URL to the current Render service URL. If your existing service already has a working `DOCINTEL_API_KEY`, preserve that value when syncing the blueprint; the portal and OCR endpoint must use the same key.

## Local development

Set the variables in your local environment, then run:

```bash
pip install -r requirements.txt
export DOCINTEL_API_KEY="your-local-api-key"
export DOCINTEL_DEMO_PASSWORD="your-demo-password"
export DOCINTEL_DEMO_SESSION_SECRET="a-long-random-local-session-secret"
export DOCINTEL_UPSTREAM_API_URL="http://127.0.0.1:8000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/app`. The secure cookie flag is enabled automatically when the request uses HTTPS.

## Demo behavior and limitations

- Files are streamed from the browser to the portal backend, then forwarded to the OCR API as multipart form data.
- The portal enforces a 15 MB upload cap. The OCR API performs its own format, file signature, page-count and image validation.
- The browser displays extracted values and the complete JSON response; it does not persist uploaded documents or processing history.
- The UI warns users to verify extracted values. OCR confidence is not proof of document authenticity.
- This is a single-user demo foundation, not a multi-tenant production document management system. Before external users or sensitive production documents are enabled, add rate limiting, audit logging, retention/deletion controls, CSRF review, monitoring and an explicit data-protection policy.
