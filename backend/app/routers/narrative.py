from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from app.models.narrative import NarrativeSummary
from app.services.analytics import build_analytics_report
from app.services.narrative import (
    GroqLLMClient,
    build_unavailable_summary,
    generate_narrative_summary,
)
from app.services.reconciliation import build_reconciliation_report
from app.services.validation import parse_billing_log

router = APIRouter(prefix="/narrative", tags=["narrative"])


@router.post("", response_model=NarrativeSummary)
async def post_narrative(rows: Any = Body(...)) -> NarrativeSummary:
    """Validate a raw billing log, then generate and citation-check the AI
    narrative summary against the deterministic reconciliation/analytics
    reports built from it.

    Malformed billing log rows still raise BillingLogValidationError (422,
    handled in app.main), same as the other endpoints. Once the log itself
    is valid, this endpoint always returns 200 with a NarrativeSummary
    body: any narrative-generation failure - LLM client misconfigured
    (e.g. missing GROQ_API_KEY), a network error, or malformed model
    output - surfaces as `generation_error` on that body rather than a
    5xx, so the frontend has exactly one response shape to render
    regardless of cause.
    """
    entries = parse_billing_log(rows)
    reconciliation = build_reconciliation_report(entries)
    analytics = build_analytics_report(entries)

    try:
        llm_client = GroqLLMClient()
    except Exception as exc:  # e.g. GROQ_API_KEY not set
        return build_unavailable_summary(exc)

    return generate_narrative_summary(reconciliation, analytics, llm_client)
