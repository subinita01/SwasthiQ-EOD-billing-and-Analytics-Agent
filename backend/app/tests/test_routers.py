from __future__ import annotations

import copy


def test_health(api_client):
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_post_reconciliation_success(api_client, clinic_day_1_raw):
    response = api_client.post("/reconciliation", json=clinic_day_1_raw)

    assert response.status_code == 200
    body = response.json()
    assert body["billed_paise"] == 7450
    assert body["collected_paise"] == 6750
    assert body["outstanding_paise"] == 700
    assert body["refunds_paise"] == 500
    assert len(body["payment_mode_breakdown"]) == 3


def test_post_analytics_success(api_client, clinic_day_1_raw):
    response = api_client.post("/analytics", json=clinic_day_1_raw)

    assert response.status_code == 200
    body = response.json()
    assert body["peak_hour"] == 14
    assert [r["drug_name"] for r in body["top_medicines_by_quantity"]] == [
        "Bandage",
        "Paracetamol",
        "Cough Syrup",
    ]
    assert [r["drug_name"] for r in body["top_medicines_by_revenue"]] == [
        "Cough Syrup",
        "Paracetamol",
        "Bandage",
    ]


def test_post_report_combines_both_and_matches_individual_endpoints(api_client, clinic_day_1_raw):
    reconciliation_response = api_client.post("/reconciliation", json=clinic_day_1_raw)
    analytics_response = api_client.post("/analytics", json=clinic_day_1_raw)
    report_response = api_client.post("/report", json=clinic_day_1_raw)

    assert report_response.status_code == 200
    body = report_response.json()
    assert body["reconciliation"] == reconciliation_response.json()
    assert body["analytics"] == analytics_response.json()


def _make_malformed_rows(clinic_day_1_raw):
    rows = copy.deepcopy(clinic_day_1_raw)
    del rows[0]["visit_id"]  # missing required field
    rows[2]["line_items"][0]["qty"] = -5  # negative qty
    return rows


def test_post_reconciliation_malformed_rows_returns_structured_422(api_client, clinic_day_1_raw):
    response = api_client.post("/reconciliation", json=_make_malformed_rows(clinic_day_1_raw))

    assert response.status_code == 422
    body = response.json()
    assert "errors" in body
    fields = {e["field"] for e in body["errors"]}
    assert "visit_id" in fields
    assert any("qty" in f for f in fields)


def test_post_analytics_malformed_rows_returns_structured_422(api_client, clinic_day_1_raw):
    response = api_client.post("/analytics", json=_make_malformed_rows(clinic_day_1_raw))

    assert response.status_code == 422
    body = response.json()
    assert "errors" in body
    assert len(body["errors"]) >= 2


def test_post_report_malformed_rows_returns_structured_422(api_client, clinic_day_1_raw):
    response = api_client.post("/report", json=_make_malformed_rows(clinic_day_1_raw))

    assert response.status_code == 422
    body = response.json()
    assert "errors" in body


def test_post_reconciliation_with_non_list_body_returns_same_structured_422(api_client):
    response = api_client.post("/reconciliation", json={"not": "a list"})

    assert response.status_code == 422
    body = response.json()
    assert "errors" in body
    assert body["errors"][0]["row_index"] == -1
    assert "array" in body["errors"][0]["message"].lower()


def test_post_analytics_with_row_that_is_not_an_object_returns_structured_422(api_client):
    response = api_client.post("/analytics", json=[1, 2, 3])

    assert response.status_code == 422
    body = response.json()
    assert all(e["message"] == "Row must be a JSON object" for e in body["errors"])


def test_post_report_with_empty_log_returns_zeroed_reports(api_client):
    response = api_client.post("/report", json=[])

    assert response.status_code == 200
    body = response.json()
    assert body["reconciliation"]["billed_paise"] == 0
    assert body["analytics"]["peak_hour"] is None
