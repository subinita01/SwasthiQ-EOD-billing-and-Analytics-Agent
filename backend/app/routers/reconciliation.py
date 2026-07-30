from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from app.models.report import ReconciliationReport
from app.services.reconciliation import build_reconciliation_report
from app.services.validation import parse_billing_log

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


@router.post("", response_model=ReconciliationReport)
async def post_reconciliation(rows: Any = Body(...)) -> ReconciliationReport:
    """Validate a raw billing log and return the EOD reconciliation report.

    Any malformed row, or a malformed payload shape entirely, raises
    BillingLogValidationError, which app.main's exception handler turns
    into a 422 with a per-row/per-field error list rather than a 500.
    """
    entries = parse_billing_log(rows)
    return build_reconciliation_report(entries)
