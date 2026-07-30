from __future__ import annotations

import copy

import pytest

from app.services.validation import BillingLogValidationError, parse_billing_log

VALID_ROW = {
    "clinic_id": "clinic-1",
    "visit_id": "visit-1",
    "timestamp": "2026-07-30T09:15:00Z",
    "doctor_id": "doc-1",
    "line_items": [
        {"drug_name": "Paracetamol", "qty": 2, "unit_price_paise": 500},
    ],
    "payment_mode": "cash",
    "amount_paid_paise": 1000,
    "discount_paise": 0,
    "is_refund": False,
}


def _row(**overrides):
    row = copy.deepcopy(VALID_ROW)
    row.update(overrides)
    return row


def test_valid_log_parses_all_rows():
    entries = parse_billing_log([VALID_ROW, VALID_ROW])
    assert len(entries) == 2
    assert entries[0].visit_id == "visit-1"


def test_missing_required_field_raises_specific_error():
    row = _row()
    del row["visit_id"]

    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log([row])

    errors = exc_info.value.errors
    assert len(errors) == 1
    assert errors[0].row_index == 0
    assert errors[0].field == "visit_id"
    assert "required" in errors[0].message.lower()


def test_wrong_type_raises_specific_error():
    row = _row(amount_paid_paise="not-a-number")

    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log([row])

    errors = exc_info.value.errors
    assert len(errors) == 1
    assert errors[0].row_index == 0
    assert errors[0].field == "amount_paid_paise"
    assert errors[0].invalid_value == "not-a-number"


def test_float_money_is_rejected_not_silently_coerced():
    row = _row(discount_paise=10.5)

    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log([row])

    errors = exc_info.value.errors
    assert errors[0].field == "discount_paise"


def test_negative_qty_raises_specific_error():
    row = _row(
        line_items=[{"drug_name": "Paracetamol", "qty": -2, "unit_price_paise": 500}]
    )

    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log([row])

    errors = exc_info.value.errors
    assert len(errors) == 1
    assert errors[0].row_index == 0
    assert errors[0].field == "line_items.0.qty"
    assert errors[0].invalid_value == -2


def test_refund_flag_amount_sign_mismatch_raises_specific_error():
    row = _row(is_refund=True, amount_paid_paise=500)

    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log([row])

    errors = exc_info.value.errors
    assert len(errors) == 1
    assert "refund" in errors[0].message.lower()


def test_invalid_payment_mode_raises_specific_error():
    row = _row(payment_mode="bitcoin")

    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log([row])

    errors = exc_info.value.errors
    assert errors[0].field == "payment_mode"


def test_non_utc_timestamp_raises_specific_error():
    row = _row(timestamp="2026-07-30T09:15:00+05:30")

    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log([row])

    errors = exc_info.value.errors
    assert errors[0].field == "timestamp"
    assert "utc" in errors[0].message.lower()


def test_multiple_bad_rows_collect_all_errors_not_just_first():
    bad_row_1 = _row()
    del bad_row_1["clinic_id"]
    bad_row_2 = _row(amount_paid_paise="oops")

    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log([bad_row_1, bad_row_2])

    errors = exc_info.value.errors
    assert {e.row_index for e in errors} == {0, 1}


def test_non_list_payload_raises_specific_error():
    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log({"not": "a list"})

    errors = exc_info.value.errors
    assert errors[0].row_index == -1
    assert "array" in errors[0].message.lower()


def test_invalid_json_string_raises_specific_error():
    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log("{not valid json")

    errors = exc_info.value.errors
    assert errors[0].row_index == -1
    assert "json" in errors[0].message.lower()


def test_mixed_clinic_ids_in_one_log_raises_specific_error():
    row_a = _row(visit_id="visit-a")
    row_b = _row(visit_id="visit-b", clinic_id="clinic-2")

    with pytest.raises(BillingLogValidationError) as exc_info:
        parse_billing_log([row_a, row_b])

    errors = exc_info.value.errors
    assert len(errors) == 1
    assert errors[0].row_index == -1
    assert errors[0].field == "clinic_id"
    assert errors[0].invalid_value == ["clinic-1", "clinic-2"]


def test_single_clinic_id_across_rows_is_fine():
    entries = parse_billing_log([_row(visit_id="visit-a"), _row(visit_id="visit-b")])
    assert len(entries) == 2
