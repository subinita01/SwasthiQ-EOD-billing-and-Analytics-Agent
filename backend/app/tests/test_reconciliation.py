from __future__ import annotations

from app.models.billing import PaymentMode
from app.services.reconciliation import build_reconciliation_report


def _by_mode(report, mode: PaymentMode):
    return next(b for b in report.payment_mode_breakdown if b.payment_mode == mode)


def test_empty_log_produces_zeroed_report_for_all_modes():
    report = build_reconciliation_report([])

    assert report.billed_paise == 0
    assert report.collected_paise == 0
    assert report.outstanding_paise == 0
    assert report.refunds_paise == 0
    assert {b.payment_mode for b in report.payment_mode_breakdown} == set(PaymentMode)
    assert all(b.transaction_count == 0 for b in report.payment_mode_breakdown)


def test_clinic_day_1_totals(clinic_day_1):
    report = build_reconciliation_report(clinic_day_1)

    assert report.billed_paise == 7450
    assert report.collected_paise == 6750
    assert report.outstanding_paise == 700
    assert report.refunds_paise == 500


def test_clinic_day_1_partial_payment_shows_up_as_outstanding_on_upi(clinic_day_1):
    # visit-3: billed 1700 (1500 Paracetamol + 200 Bandage), only 1000 paid.
    report = build_reconciliation_report(clinic_day_1)
    upi = _by_mode(report, PaymentMode.UPI)

    assert upi.transaction_count == 2
    assert upi.billed_paise == 2150
    assert upi.collected_paise == 1450
    assert upi.outstanding_paise == 700
    assert upi.refunds_paise == 0


def test_clinic_day_1_refund_reduces_only_that_modes_refunds_not_billed(clinic_day_1):
    # visit-4: cash refund of 500 against the earlier cash sale (visit-1).
    report = build_reconciliation_report(clinic_day_1)
    cash = _by_mode(report, PaymentMode.CASH)

    assert cash.transaction_count == 2
    assert cash.billed_paise == 1000
    assert cash.collected_paise == 1000
    assert cash.outstanding_paise == 0
    assert cash.refunds_paise == 500


def test_clinic_day_1_card_has_no_outstanding_or_refunds(clinic_day_1):
    report = build_reconciliation_report(clinic_day_1)
    card = _by_mode(report, PaymentMode.CARD)

    assert card.transaction_count == 2
    assert card.billed_paise == 4300
    assert card.collected_paise == 4300
    assert card.outstanding_paise == 0
    assert card.refunds_paise == 0


def test_clinic_day_1_breakdown_sums_to_totals(clinic_day_1):
    report = build_reconciliation_report(clinic_day_1)
    breakdown = report.payment_mode_breakdown

    assert sum(b.billed_paise for b in breakdown) == report.billed_paise
    assert sum(b.collected_paise for b in breakdown) == report.collected_paise
    assert sum(b.refunds_paise for b in breakdown) == report.refunds_paise
    assert sum(b.outstanding_paise for b in breakdown) == report.outstanding_paise


def test_clinic_day_2_totals_with_full_discount_and_over_refund(clinic_day_2):
    # visit-102 is a fully-discounted (free) sale: billed 0, collected 0.
    # visit-107 refunds more units than visit-106 sold (data anomaly),
    # which must not crash aggregation.
    report = build_reconciliation_report(clinic_day_2)

    assert report.billed_paise == 2300
    assert report.collected_paise == 2200
    assert report.outstanding_paise == 100
    assert report.refunds_paise == 2200


def test_clinic_day_2_upi_partial_payment(clinic_day_2):
    # visit-108: billed 400, only 300 collected.
    report = build_reconciliation_report(clinic_day_2)
    upi = _by_mode(report, PaymentMode.UPI)

    assert upi.transaction_count == 3
    assert upi.billed_paise == 400
    assert upi.collected_paise == 300
    assert upi.outstanding_paise == 100
    assert upi.refunds_paise == 500


def test_clinic_day_3_all_refund_and_unused_payment_mode(clinic_day_3):
    # visit-201/202 net to a zero-sum cash refund of the exact sale amount;
    # card is never used at all in this day's log.
    report = build_reconciliation_report(clinic_day_3)
    cash = _by_mode(report, PaymentMode.CASH)
    card = _by_mode(report, PaymentMode.CARD)
    upi = _by_mode(report, PaymentMode.UPI)

    assert report.billed_paise == 1300
    assert report.collected_paise == 1300
    assert report.outstanding_paise == 0
    assert report.refunds_paise == 300

    assert cash.transaction_count == 2
    assert cash.billed_paise == 300
    assert cash.refunds_paise == 300

    assert card.transaction_count == 0
    assert card.billed_paise == 0
    assert card.collected_paise == 0
    assert card.refunds_paise == 0

    assert upi.transaction_count == 1
    assert upi.billed_paise == 1000
    assert upi.collected_paise == 1000
