from __future__ import annotations

from app.services.analytics import build_analytics_report


def _revenue_at(report, hour: int) -> int:
    return next(h.revenue_paise for h in report.revenue_by_hour if h.hour == hour)


def _qty_ranking_names(report) -> list[str]:
    return [r.drug_name for r in report.top_medicines_by_quantity]


def _revenue_ranking_names(report) -> list[str]:
    return [r.drug_name for r in report.top_medicines_by_revenue]


def test_empty_log_produces_zeroed_report_with_no_peak():
    report = build_analytics_report([])

    assert len(report.revenue_by_hour) == 24
    assert all(h.revenue_paise == 0 for h in report.revenue_by_hour)
    assert report.peak_hour is None
    assert report.top_medicines_by_quantity == []
    assert report.top_medicines_by_revenue == []
    assert report.notes == []


def test_clinic_day_1_revenue_by_hour_and_peak(clinic_day_1):
    report = build_analytics_report(clinic_day_1)

    assert _revenue_at(report, 9) == 2300  # visit-1 (1000) + visit-2 (1300)
    assert _revenue_at(report, 10) == 1000  # visit-3 partial payment
    assert _revenue_at(report, 11) == -500  # visit-4 refund
    assert _revenue_at(report, 14) == 3450  # visit-5 (3000) + visit-6 (450)
    assert report.peak_hour == 14


def test_clinic_day_1_medicine_rankings_are_distinct_orderings(clinic_day_1):
    report = build_analytics_report(clinic_day_1)

    assert _qty_ranking_names(report) == ["Bandage", "Paracetamol", "Cough Syrup"]
    assert _revenue_ranking_names(report) == ["Cough Syrup", "Paracetamol", "Bandage"]

    bandage_qty = next(r for r in report.top_medicines_by_quantity if r.drug_name == "Bandage")
    assert bandage_qty.net_qty == 7  # 2 (visit-3) + 5 (visit-6)

    paracetamol_rev = next(
        r for r in report.top_medicines_by_revenue if r.drug_name == "Paracetamol"
    )
    # (2*500 + 3*500) sold - 1*500 refunded = 2000
    assert paracetamol_rev.net_revenue_paise == 2000

    assert report.notes  # discount-attribution caveat present whenever medicines are ranked


def test_clinic_day_2_over_refund_produces_negative_net_without_crashing(clinic_day_2):
    # Cough Drops: 2 sold, 3 refunded -> net qty and revenue go negative,
    # and must still appear (at the bottom of both rankings), not be dropped.
    report = build_analytics_report(clinic_day_2)

    cough_drops_qty = next(
        r for r in report.top_medicines_by_quantity if r.drug_name == "Cough Drops"
    )
    cough_drops_rev = next(
        r for r in report.top_medicines_by_revenue if r.drug_name == "Cough Drops"
    )
    assert cough_drops_qty.net_qty == -1
    assert cough_drops_rev.net_revenue_paise == -300
    assert _qty_ranking_names(report)[-1] == "Cough Drops"
    assert _revenue_ranking_names(report)[-1] == "Cough Drops"


def test_clinic_day_2_rankings_swap_order_between_qty_and_revenue(clinic_day_2):
    report = build_analytics_report(clinic_day_2)

    assert _qty_ranking_names(report)[0] == "Vitamin C"
    assert _revenue_ranking_names(report)[0] == "Antacid"


def test_clinic_day_2_peak_hour(clinic_day_2):
    report = build_analytics_report(clinic_day_2)

    assert _revenue_at(report, 8) == 500  # visit-101 (500) + visit-102 (0)
    assert _revenue_at(report, 9) == -500  # 800 - 800 - 500
    assert _revenue_at(report, 10) == -300  # 600 - 900
    assert _revenue_at(report, 11) == 300
    assert report.peak_hour == 8


def test_clinic_day_3_zero_net_medicine_still_reported(clinic_day_3):
    # Ibuprofen is sold and then fully refunded in the same hour: net qty
    # and revenue are exactly zero, which must still show up in rankings.
    report = build_analytics_report(clinic_day_3)

    ibuprofen_qty = next(
        r for r in report.top_medicines_by_quantity if r.drug_name == "Ibuprofen"
    )
    ibuprofen_rev = next(
        r for r in report.top_medicines_by_revenue if r.drug_name == "Ibuprofen"
    )
    assert ibuprofen_qty.net_qty == 0
    assert ibuprofen_rev.net_revenue_paise == 0
    assert _revenue_at(report, 7) == 0  # 300 - 300
    assert report.peak_hour == 12
