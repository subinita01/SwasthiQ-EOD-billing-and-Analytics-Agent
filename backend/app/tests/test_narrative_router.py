from __future__ import annotations

import copy
import json


class _FakeLLMClient:
    def __init__(self, response_text: str | None = None):
        self._response_text = response_text or json.dumps(
            {"narrative": "Business as usual today.", "citations": []}
        )

    def complete(self, prompt: str) -> str:
        return self._response_text


def test_post_narrative_without_api_key_returns_graceful_200_not_500(
    api_client, clinic_day_1_raw, monkeypatch
):
    # Force the "not configured" path regardless of the host environment,
    # so this test never depends on (or risks) a real network call.
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    response = api_client.post("/narrative", json=clinic_day_1_raw)

    assert response.status_code == 200
    body = response.json()
    assert body["generation_error"] is not None
    assert "GROQ_API_KEY" in body["generation_error"]
    assert body["fully_verified"] is False
    assert body["traced_figures"] == []
    assert body["narrative"]  # safe fallback text, not empty


def test_post_narrative_malformed_rows_returns_structured_422(api_client, clinic_day_1_raw):
    rows = copy.deepcopy(clinic_day_1_raw)
    del rows[0]["visit_id"]

    response = api_client.post("/narrative", json=rows)

    assert response.status_code == 422
    body = response.json()
    assert "errors" in body
    assert body["errors"][0]["field"] == "visit_id"


def test_post_narrative_with_working_llm_client_returns_verified_summary(
    api_client, clinic_day_1_raw, monkeypatch
):
    monkeypatch.setattr(
        "app.routers.narrative.GroqLLMClient", lambda: _FakeLLMClient()
    )

    response = api_client.post("/narrative", json=clinic_day_1_raw)

    assert response.status_code == 200
    body = response.json()
    assert body["generation_error"] is None
    assert body["fully_verified"] is True
    assert body["narrative"] == "Business as usual today."
    assert body["traced_figures"] == []


def test_post_narrative_surfaces_llm_output_validation_issues_without_crashing(
    api_client, clinic_day_1_raw, monkeypatch
):
    # LLM cites a field that doesn't exist in the report - should still be
    # a 200 with the bad citation flagged, not a 500 or a silently-trusted
    # response.
    bad_response = json.dumps(
        {
            "narrative": "Profit today was ₹20.00.",
            "citations": [
                {
                    "field": "reconciliation.profit_paise",
                    "value": 2000,
                    "displayed_text": "₹20.00",
                }
            ],
        }
    )
    monkeypatch.setattr(
        "app.routers.narrative.GroqLLMClient", lambda: _FakeLLMClient(bad_response)
    )

    response = api_client.post("/narrative", json=clinic_day_1_raw)

    assert response.status_code == 200
    body = response.json()
    assert body["generation_error"] is None
    assert body["fully_verified"] is False
    assert len(body["traced_figures"]) == 1
    assert body["traced_figures"][0]["verified"] is False


def test_post_narrative_with_llm_returning_garbage_degrades_gracefully(
    api_client, clinic_day_1_raw, monkeypatch
):
    monkeypatch.setattr(
        "app.routers.narrative.GroqLLMClient",
        lambda: _FakeLLMClient("not valid json at all"),
    )

    response = api_client.post("/narrative", json=clinic_day_1_raw)

    assert response.status_code == 200
    body = response.json()
    assert body["generation_error"] is not None
    assert body["fully_verified"] is False
