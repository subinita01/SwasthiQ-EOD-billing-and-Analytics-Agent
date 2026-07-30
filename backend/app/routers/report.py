from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from app.models.report import EODReport
from app.services.analytics import build_analytics_report
from app.services.reconciliation import build_reconciliation_report
from app.services.validation import parse_billing_log

router = APIRouter(prefix="/report", tags=["report"])


@router.post("", response_model=EODReport)
async def post_report(rows: Any = Body(...)) -> EODReport:
    """Validate a raw billing log once and return both the reconciliation
    and analytics reports together, so the frontend doesn't have to submit
    (and re-validate) the same log twice for two of its three screens.

    Any malformed row, or a malformed payload shape entirely, raises
    BillingLogValidationError, which app.main's exception handler turns
    into a 422 with a per-row/per-field error list rather than a 500.
    """
    entries = parse_billing_log(rows)
    return EODReport(
        reconciliation=build_reconciliation_report(entries),
        analytics=build_analytics_report(entries),
    )
