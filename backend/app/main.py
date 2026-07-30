from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()  # backend/.env - e.g. GROQ_API_KEY, CORS_ALLOWED_ORIGINS

from app.routers import analytics, billing, narrative, reconciliation, report  # noqa: E402
from app.services.validation import BillingLogValidationError  # noqa: E402

app = FastAPI(title="SwasthiQ EOD Billing & Analytics Agent")

# Frontend dev server (Vite) runs on a different origin than the API, so the
# browser needs an explicit CORS allow. CORS_ALLOWED_ORIGINS can override the
# default for other deployments; unset defaults to the Vite dev server only.
_allowed_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BillingLogValidationError)
async def billing_log_validation_error_handler(
    request: Request, exc: BillingLogValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content=exc.to_dict())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(billing.router)
app.include_router(reconciliation.router)
app.include_router(analytics.router)
app.include_router(report.router)
app.include_router(narrative.router)
