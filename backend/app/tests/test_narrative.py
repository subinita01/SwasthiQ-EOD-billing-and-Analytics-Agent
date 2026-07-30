from __future__ import annotations

import json

from app.services.narrative import build_figure_index, generate_narrative_summary


class FakeLLMClient:
    def __init__(self, response_text: str):
        self._response_text = response_text

    def complete(self, prompt: str) -> str:
        return self._response_text


def _well_formed_response() -> str:
    payload = {
        "narrative": (
            "Today the clinic billed ₹74.50 and collected ₹67.50, leaving "
            "₹7.00 outstanding, with ₹5.00 refunded. The busiest hour was 14, "
            "bringing in ₹34.50. Bandage was the top seller by quantity, while "
            "Cough Syrup led by revenue."
        ),
        "citations": [
            {"field": "reconciliation.billed_paise", "value": 7450, "displayed_text": "₹74.50"},
            {"field": "reconciliation.collected_paise", "value": 6750, "displayed_text": "₹67.50"},
            {"field": "reconciliation.outstanding_paise", "value": 700, "displayed_text": "₹7.00"},
            {"field": "reconciliation.refunds_paise", "value": 500, "displayed_text": "₹5.00"},
            {"field": "analytics.peak_hour", "value": 14, "displayed_text": "14"},
            {
                "field": "analytics.revenue_by_hour.14.revenue_paise",
                "value": 3450,
                "displayed_text": "₹34.50",
            },
        ],
    }
    return json.dumps(payload)


def test_build_figure_index_matches_reconciliation_and_analytics(clinic_day_1_reports):
    reconciliation, analytics = clinic_day_1_reports
    index = build_figure_index(reconciliation, analytics)

    assert index["reconciliation.billed_paise"] == 7450
    assert index["reconciliation.collected_paise"] == 6750
    assert index["reconciliation.outstanding_paise"] == 700
    assert index["reconciliation.refunds_paise"] == 500
    assert index["reconciliation.payment_mode_breakdown.upi.outstanding_paise"] == 700
    assert index["analytics.peak_hour"] == 14
    assert index["analytics.revenue_by_hour.14.revenue_paise"] == 3450
    assert index["analytics.top_medicines_by_quantity.Bandage.net_qty"] == 7
    assert index["analytics.top_medicines_by_revenue.Cough Syrup.net_revenue_paise"] == 4500


def test_build_figure_index_omits_peak_hour_when_no_data():
    from app.services.analytics import build_analytics_report
    from app.services.reconciliation import build_reconciliation_report

    reconciliation = build_reconciliation_report([])
    analytics = build_analytics_report([])
    index = build_figure_index(reconciliation, analytics)

    assert "analytics.peak_hour" not in index
    assert index["reconciliation.billed_paise"] == 0


def test_well_formed_response_is_fully_verified(clinic_day_1_reports):
    reconciliation, analytics = clinic_day_1_reports
    summary = generate_narrative_summary(
        reconciliation, analytics, FakeLLMClient(_well_formed_response())
    )

    assert summary.generation_error is None
    assert summary.fully_verified is True
    assert len(summary.traced_figures) == 6
    assert all(fig.verified for fig in summary.traced_figures)


def test_citation_with_unknown_field_is_flagged_not_crashed(clinic_day_1_reports):
    reconciliation, analytics = clinic_day_1_reports
    payload = {
        "narrative": "The clinic made a profit of ₹20.00 today.",
        "citations": [
            {
                "field": "reconciliation.profit_paise",
                "value": 2000,
                "displayed_text": "₹20.00",
            }
        ],
    }
    summary = generate_narrative_summary(
        reconciliation, analytics, FakeLLMClient(json.dumps(payload))
    )

    assert summary.generation_error is None
    assert summary.fully_verified is False
    assert len(summary.traced_figures) == 1
    figure = summary.traced_figures[0]
    assert figure.verified is False
    assert "unknown field" in figure.issues[0]


def test_citation_with_wrong_value_is_flagged(clinic_day_1_reports):
    reconciliation, analytics = clinic_day_1_reports
    payload = {
        "narrative": "The clinic billed ₹100.00 today.",
        "citations": [
            {
                "field": "reconciliation.billed_paise",
                "value": 10000,
                "displayed_text": "₹100.00",
            }
        ],
    }
    summary = generate_narrative_summary(
        reconciliation, analytics, FakeLLMClient(json.dumps(payload))
    )

    assert summary.fully_verified is False
    figure = summary.traced_figures[0]
    assert figure.verified is False
    assert "does not match report value" in figure.issues[0]


def test_displayed_text_not_matching_cited_value_is_flagged(clinic_day_1_reports):
    # Right field, right raw value, but the prose text shows a different
    # number than the value it claims to represent - a subtler hallucination.
    reconciliation, analytics = clinic_day_1_reports
    payload = {
        "narrative": "The clinic billed ₹100.00 today.",
        "citations": [
            {
                "field": "reconciliation.billed_paise",
                "value": 7450,
                "displayed_text": "₹100.00",
            }
        ],
    }
    summary = generate_narrative_summary(
        reconciliation, analytics, FakeLLMClient(json.dumps(payload))
    )

    assert summary.fully_verified is False
    figure = summary.traced_figures[0]
    assert figure.verified is False
    assert any("resolves to" in issue for issue in figure.issues)


def test_uncited_number_in_narrative_is_flagged(clinic_day_1_reports):
    reconciliation, analytics = clinic_day_1_reports
    payload = {
        "narrative": "The clinic billed ₹74.50 today and saw 42 walk-ins.",
        "citations": [
            {
                "field": "reconciliation.billed_paise",
                "value": 7450,
                "displayed_text": "₹74.50",
            }
        ],
    }
    summary = generate_narrative_summary(
        reconciliation, analytics, FakeLLMClient(json.dumps(payload))
    )

    assert summary.fully_verified is False
    uncited = [f for f in summary.traced_figures if f.field == "<uncited>"]
    assert len(uncited) == 1
    assert uncited[0].displayed_text == "42"


def test_drug_names_with_digits_in_ids_are_not_mistaken_for_citations(clinic_day_1_reports):
    reconciliation, analytics = clinic_day_1_reports
    payload = {
        "narrative": "Visit-3 and clinic-1 processed no separately citable figures here.",
        "citations": [],
    }
    summary = generate_narrative_summary(
        reconciliation, analytics, FakeLLMClient(json.dumps(payload))
    )

    assert summary.fully_verified is True
    assert summary.traced_figures == []


def test_malformed_json_degrades_gracefully_without_crashing(clinic_day_1_reports):
    reconciliation, analytics = clinic_day_1_reports
    summary = generate_narrative_summary(
        reconciliation, analytics, FakeLLMClient("this is not { json at all")
    )

    assert summary.generation_error is not None
    assert "JSONDecodeError" in summary.generation_error
    assert summary.fully_verified is False
    assert summary.traced_figures == []
    assert summary.narrative  # safe fallback text, not empty/crashed


def test_missing_required_field_in_llm_response_degrades_gracefully(clinic_day_1_reports):
    reconciliation, analytics = clinic_day_1_reports
    summary = generate_narrative_summary(
        reconciliation, analytics, FakeLLMClient(json.dumps({"citations": []}))
    )

    assert summary.generation_error is not None
    assert "ValidationError" in summary.generation_error
    assert summary.fully_verified is False


def test_wrong_type_in_llm_response_degrades_gracefully(clinic_day_1_reports):
    reconciliation, analytics = clinic_day_1_reports
    payload = {"narrative": "ok", "citations": "not-a-list"}
    summary = generate_narrative_summary(
        reconciliation, analytics, FakeLLMClient(json.dumps(payload))
    )

    assert summary.generation_error is not None
    assert summary.fully_verified is False


def test_markdown_fenced_json_is_still_parsed(clinic_day_1_reports):
    reconciliation, analytics = clinic_day_1_reports
    payload = {
        "narrative": "The clinic billed ₹74.50 today.",
        "citations": [
            {
                "field": "reconciliation.billed_paise",
                "value": 7450,
                "displayed_text": "₹74.50",
            }
        ],
    }
    fenced = "```json\n" + json.dumps(payload) + "\n```"

    summary = generate_narrative_summary(reconciliation, analytics, FakeLLMClient(fenced))

    assert summary.generation_error is None
    assert summary.fully_verified is True


def test_llm_client_raising_an_exception_degrades_gracefully(clinic_day_1_reports):
    class ExplodingLLMClient:
        def complete(self, prompt: str) -> str:
            raise RuntimeError("network is down")

    reconciliation, analytics = clinic_day_1_reports
    summary = generate_narrative_summary(reconciliation, analytics, ExplodingLLMClient())

    assert summary.generation_error is not None
    assert "network is down" in summary.generation_error
    assert summary.fully_verified is False


def test_empty_log_narrative_with_no_citations_is_trivially_verified():
    from app.services.analytics import build_analytics_report
    from app.services.reconciliation import build_reconciliation_report

    reconciliation = build_reconciliation_report([])
    analytics = build_analytics_report([])
    payload = {
        "narrative": "No transactions were recorded today.",
        "citations": [],
    }
    summary = generate_narrative_summary(
        reconciliation, analytics, FakeLLMClient(json.dumps(payload))
    )

    assert summary.fully_verified is True
    assert summary.traced_figures == []
