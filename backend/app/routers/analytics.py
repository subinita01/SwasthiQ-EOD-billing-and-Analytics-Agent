from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from app.models.report import AnalyticsReport
from app.services.analytics import build_analytics_report
from app.services.validation import parse_billing_log

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("", response_model=AnalyticsReport)
async def post_analytics(rows: Any = Body(...)) -> AnalyticsReport:
    """Validate a raw billing log and return the analytics report.

    Any malformed row, or a malformed payload shape entirely, raises
    BillingLogValidationError, which app.main's exception handler turns
    into a 422 with a per-row/per-field error list rather than a 500.
    """
    entries = parse_billing_log(rows)
    return build_analytics_report(entries)
