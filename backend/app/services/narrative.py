from __future__ import annotations

import json
import os
import re
from typing import Protocol

from pydantic import BaseModel, Field

from app.models.narrative import NarrativeSummary, TracedFigure
from app.models.report import AnalyticsReport, ReconciliationReport

# Numbers written in narrative prose, e.g. "₹74.50", "7,450", "14". Excludes
# digits fused to letters/hyphens (drug names, IDs like "visit-1") via the
# lookaround, so identifiers are never mistaken for cited figures.
NUMBER_TOKEN_PATTERN = re.compile(r"(?<![\w-])₹?-?\d[\d,]*(?:\.\d+)?(?!\w)")


# ---------------------------------------------------------------------------
# Figure index: the flat, ground-truth set of numbers the narrative may cite.
# Built directly from the deterministic reports - nothing here is invented.
# ---------------------------------------------------------------------------


def build_figure_index(
    reconciliation: ReconciliationReport, analytics: AnalyticsReport
) -> dict[str, int]:
    index: dict[str, int] = {
        "reconciliation.billed_paise": reconciliation.billed_paise,
        "reconciliation.collected_paise": reconciliation.collected_paise,
        "reconciliation.outstanding_paise": reconciliation.outstanding_paise,
        "reconciliation.refunds_paise": reconciliation.refunds_paise,
    }
    for breakdown in reconciliation.payment_mode_breakdown:
        prefix = f"reconciliation.payment_mode_breakdown.{breakdown.payment_mode.value}"
        index[f"{prefix}.transaction_count"] = breakdown.transaction_count
        index[f"{prefix}.billed_paise"] = breakdown.billed_paise
        index[f"{prefix}.collected_paise"] = breakdown.collected_paise
        index[f"{prefix}.outstanding_paise"] = breakdown.outstanding_paise
        index[f"{prefix}.refunds_paise"] = breakdown.refunds_paise

    if analytics.peak_hour is not None:
        index["analytics.peak_hour"] = analytics.peak_hour
    for hourly in analytics.revenue_by_hour:
        index[f"analytics.revenue_by_hour.{hourly.hour}.revenue_paise"] = hourly.revenue_paise
    for ranking in analytics.top_medicines_by_quantity:
        index[f"analytics.top_medicines_by_quantity.{ranking.drug_name}.net_qty"] = (
            ranking.net_qty
        )
    for ranking in analytics.top_medicines_by_revenue:
        index[f"analytics.top_medicines_by_revenue.{ranking.drug_name}.net_revenue_paise"] = (
            ranking.net_revenue_paise
        )

    return index


# ---------------------------------------------------------------------------
# LLM client abstraction. generate_narrative_summary depends only on this
# Protocol, so tests can inject a fake client instead of calling a real API.
# ---------------------------------------------------------------------------


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str: ...


class GroqLLMClient:
    """Thin wrapper around the Groq SDK (free tier, OpenAI-compatible chat
    completions). Reads config from env vars so no API key is ever
    hardcoded: GROQ_API_KEY (required, free from console.groq.com),
    NARRATIVE_MODEL (optional, defaults to llama-3.3-70b-versatile).
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or os.environ.get("GROQ_API_KEY")
        self._model = model or os.environ.get("NARRATIVE_MODEL", "llama-3.3-70b-versatile")
        if not self._api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")

    def complete(self, prompt: str) -> str:
        from groq import Groq  # imported lazily: only required when this client is used

        client = Groq(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def build_prompt(figure_index: dict[str, int]) -> str:
    figures_json = json.dumps(figure_index, indent=2, sort_keys=True)
    return f"""You are writing an end-of-day (EOD) narrative summary of a clinic's billing report for clinic staff.

FIGURES below is the complete, authoritative set of numbers you are allowed to reference. \
All money values are integer paise (100 paise = ₹1). Do not invent, estimate, round in a \
misleading way, or compute any number that is not directly present in FIGURES - for example, \
profit cannot be mentioned since no cost-price data exists anywhere in FIGURES; if a figure a \
reader might expect is simply absent from FIGURES (e.g. no peak hour because there were no \
transactions), say so plainly instead of guessing. Do not write percentages, ratios, dates, \
IDs, or any other numbers that are not literal values from FIGURES.

FIGURES:
{figures_json}

Respond with ONLY a single JSON object, no markdown fences and no prose outside the JSON:
{{
  "narrative": "<2-4 short paragraphs, plain language, for clinic staff>",
  "citations": [
    {{
      "field": "<dotted field path copied exactly from a FIGURES key>",
      "value": <integer, must equal FIGURES[field] exactly>,
      "displayed_text": "<the exact substring as it appears in narrative, e.g. '₹74.50' or '14'>"
    }}
  ]
}}

Every number that appears anywhere in "narrative" must have exactly one matching entry in \
"citations" whose "displayed_text" is that exact substring. Money may be displayed as rupees \
(e.g. "₹74.50" for the FIGURES value 7450) or as raw paise; either is fine as long as \
"value" is the raw integer copied from FIGURES.
"""


# ---------------------------------------------------------------------------
# Raw LLM response parsing (untrusted external input - lenient parse, fails
# closed rather than raising past this module)
# ---------------------------------------------------------------------------


class _LLMCitation(BaseModel):
    field: str
    value: int
    displayed_text: str


class _LLMNarrativeResponse(BaseModel):
    narrative: str
    citations: list[_LLMCitation] = Field(default_factory=list)


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text[3:]
        if text.lower().startswith("json"):
            text = text[4:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _parse_llm_response(raw_text: str) -> _LLMNarrativeResponse:
    data = json.loads(_strip_markdown_fence(raw_text))
    return _LLMNarrativeResponse.model_validate(data)


# ---------------------------------------------------------------------------
# Citation validation - the ground-truth check. Every citation is verified
# against the figure index and against the narrative text itself; every
# number-looking token in the narrative must in turn be covered by a
# citation. Nothing here trusts the LLM's self-report.
# ---------------------------------------------------------------------------


def _normalize_numeric_text(text: str) -> int | None:
    cleaned = text.replace("₹", "").replace(",", "").strip()
    if not re.fullmatch(r"-?\d+(\.\d+)?", cleaned):
        return None
    if "." in cleaned:
        return round(float(cleaned) * 100)
    return int(cleaned)


def _validate_citations(
    narrative_text: str,
    citations: list[_LLMCitation],
    figure_index: dict[str, int],
) -> tuple[list[TracedFigure], bool]:
    traced: list[TracedFigure] = []
    fully_verified = True

    for citation in citations:
        issues: list[str] = []

        if citation.field not in figure_index:
            issues.append(f"unknown field '{citation.field}' is not present in the report")
        elif figure_index[citation.field] != citation.value:
            issues.append(
                f"cited value {citation.value} does not match report value "
                f"{figure_index[citation.field]} for field '{citation.field}'"
            )

        normalized = _normalize_numeric_text(citation.displayed_text)
        if normalized is None:
            issues.append(f"displayed_text '{citation.displayed_text}' is not a recognizable number")
        elif normalized != citation.value:
            issues.append(
                f"displayed_text '{citation.displayed_text}' resolves to {normalized}, "
                f"not the cited value {citation.value}"
            )

        if citation.displayed_text not in narrative_text:
            issues.append("displayed_text does not appear verbatim in the narrative")

        verified = not issues
        fully_verified = fully_verified and verified
        traced.append(
            TracedFigure(
                field=citation.field,
                value=citation.value,
                displayed_text=citation.displayed_text,
                verified=verified,
                issues=issues,
            )
        )

    cited_texts = {c.displayed_text for c in citations}
    for match in NUMBER_TOKEN_PATTERN.finditer(narrative_text):
        # Trailing commas are sentence punctuation (e.g. "...hour was 14,
        # bringing..."), not thousands separators, since a real grouping
        # comma is always followed by more digits - strip it before
        # comparing against declared citation text.
        token = match.group(0).rstrip(",")
        if token not in cited_texts:
            fully_verified = False
            traced.append(
                TracedFigure(
                    field="<uncited>",
                    value=_normalize_numeric_text(token),
                    displayed_text=token,
                    verified=False,
                    issues=["number appears in narrative text but has no matching citation"],
                )
            )

    return traced, fully_verified


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def build_unavailable_summary(exc: Exception) -> NarrativeSummary:
    """The safe, generic fallback used whenever narrative generation fails
    for any reason - bad/malformed LLM output, an LLM client that couldn't
    even be constructed (e.g. missing API key), a network error, etc. -
    so callers always get a valid NarrativeSummary shape back instead of
    an exception, regardless of which stage failed.
    """
    return NarrativeSummary(
        narrative="AI narrative summary is unavailable right now.",
        traced_figures=[],
        fully_verified=False,
        generation_error=f"{type(exc).__name__}: {exc}",
    )


def generate_narrative_summary(
    reconciliation: ReconciliationReport,
    analytics: AnalyticsReport,
    llm_client: LLMClient,
) -> NarrativeSummary:
    """Generate and validate the AI narrative summary.

    Never raises on a bad LLM response: JSON decode errors, schema
    violations, or any other failure while calling the model degrade to a
    safe fallback NarrativeSummary with `generation_error` set, rather than
    crashing or silently returning corrupted/unverified text as if it were
    trustworthy.
    """
    figure_index = build_figure_index(reconciliation, analytics)
    prompt = build_prompt(figure_index)

    try:
        raw_text = llm_client.complete(prompt)
        parsed = _parse_llm_response(raw_text)
    except Exception as exc:  # noqa: BLE001 - any LLM/parse failure must degrade, never crash
        return build_unavailable_summary(exc)

    traced_figures, fully_verified = _validate_citations(
        narrative_text=parsed.narrative,
        citations=parsed.citations,
        figure_index=figure_index,
    )

    return NarrativeSummary(
        narrative=parsed.narrative,
        traced_figures=traced_figures,
        fully_verified=fully_verified,
        generation_error=None,
    )
