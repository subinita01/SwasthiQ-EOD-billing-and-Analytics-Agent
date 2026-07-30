from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.models.billing import BillingLogEntry


@dataclass
class RowError:
    row_index: int
    field: str
    message: str
    invalid_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_index": self.row_index,
            "field": self.field,
            "message": self.message,
            "invalid_value": self.invalid_value,
        }


class BillingLogValidationError(Exception):
    """One or more rows in a billing log failed validation.

    Carries a structured, per-row/per-field error list (instead of a single
    generic message) so callers can report exactly what is wrong, in every
    row, in one pass.
    """

    def __init__(self, errors: list[RowError]):
        self.errors = errors
        super().__init__(f"{len(errors)} invalid row(s) in billing log")

    def to_dict(self) -> dict[str, Any]:
        return {"detail": str(self), "errors": [e.to_dict() for e in self.errors]}


def parse_billing_log(raw: str | list[Any]) -> list[BillingLogEntry]:
    """Parse and validate a raw billing log into BillingLogEntry rows.

    `raw` may be a JSON string or an already-decoded list. Every row is
    checked; on failure, raises BillingLogValidationError containing one
    RowError per problem found across all rows (not just the first).

    A billing log is one clinic's daily log (REFERENCE.md), and every
    downstream report aggregates across all rows with no per-clinic
    grouping - so rows spanning more than one clinic_id would silently
    blend two clinics' figures into one report with no indication. That's
    treated as a malformed payload, not a valid multi-clinic input.
    """
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BillingLogValidationError(
                [RowError(row_index=-1, field="<root>", message=f"Invalid JSON: {exc.msg}")]
            ) from exc
    else:
        data = raw

    if not isinstance(data, list):
        raise BillingLogValidationError(
            [
                RowError(
                    row_index=-1,
                    field="<root>",
                    message="Billing log must be a JSON array of rows",
                    invalid_value=type(data).__name__,
                )
            ]
        )

    entries: list[BillingLogEntry] = []
    errors: list[RowError] = []

    for index, row in enumerate(data):
        if not isinstance(row, dict):
            errors.append(
                RowError(
                    row_index=index,
                    field="<row>",
                    message="Row must be a JSON object",
                    invalid_value=row,
                )
            )
            continue
        try:
            entries.append(BillingLogEntry.model_validate(row))
        except ValidationError as exc:
            for err in exc.errors():
                field_path = ".".join(str(part) for part in err["loc"]) or "<row>"
                errors.append(
                    RowError(
                        row_index=index,
                        field=field_path,
                        message=err["msg"],
                        invalid_value=err.get("input"),
                    )
                )

    if errors:
        raise BillingLogValidationError(errors)

    distinct_clinic_ids = sorted({entry.clinic_id for entry in entries})
    if len(distinct_clinic_ids) > 1:
        raise BillingLogValidationError(
            [
                RowError(
                    row_index=-1,
                    field="clinic_id",
                    message=(
                        "Billing log must contain rows for exactly one clinic_id, found "
                        f"{len(distinct_clinic_ids)}"
                    ),
                    invalid_value=distinct_clinic_ids,
                )
            ]
        )

    return entries
