from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from app.services.validation import parse_billing_log

router = APIRouter(prefix="/billing-log", tags=["billing-log"])


@router.post("/validate")
async def validate_billing_log(rows: Any = Body(...)) -> dict:
    """Validate a raw billing log payload.

    Returns the count of valid rows on success. On any malformed row - or
    a malformed payload shape entirely (not a list, rows that aren't
    objects, etc.) - the BillingLogValidationError exception handler (see
    app.main) turns this into a single, consistently-shaped 422 with a
    per-row/per-field error list, instead of a 500 or FastAPI's separate
    default validation-error format.
    """
    entries = parse_billing_log(rows)
    return {"valid_row_count": len(entries)}
