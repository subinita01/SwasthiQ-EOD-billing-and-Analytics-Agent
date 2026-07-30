from __future__ import annotations

from dataclasses import dataclass

from app.models.billing import BillingLogEntry, PaymentMode
from app.models.report import PaymentModeBreakdown, ReconciliationReport


def _line_items_total_paise(entry: BillingLogEntry) -> int:
    return sum(item.qty * item.unit_price_paise for item in entry.line_items)


@dataclass
class _ModeAccumulator:
    transaction_count: int = 0
    billed_paise: int = 0
    collected_paise: int = 0
    refunds_paise: int = 0


def build_reconciliation_report(entries: list[BillingLogEntry]) -> ReconciliationReport:
    """Build the EOD reconciliation report, totals and per-payment-mode.

    Definitions (all integer paise):
    - billed_paise: line-item total minus discount, on non-refund rows only.
    - collected_paise: amount_paid_paise on non-refund rows only (gross
      sales collections; refunds are tracked separately, not netted in).
    - outstanding_paise: billed_paise - collected_paise. Positive means a
      sale row was paid for less than it was billed (partial payment).
    - refunds_paise: amount actually refunded, as a positive magnitude,
      from rows where is_refund is true (amount_paid_paise <= 0 there by
      the schema's sign-consistency rule).
    """
    accumulators: dict[PaymentMode, _ModeAccumulator] = {
        mode: _ModeAccumulator() for mode in PaymentMode
    }

    for entry in entries:
        acc = accumulators[entry.payment_mode]
        acc.transaction_count += 1

        if entry.is_refund:
            acc.refunds_paise += -entry.amount_paid_paise
        else:
            acc.billed_paise += _line_items_total_paise(entry) - entry.discount_paise
            acc.collected_paise += entry.amount_paid_paise

    payment_mode_breakdown = [
        PaymentModeBreakdown(
            payment_mode=mode,
            transaction_count=acc.transaction_count,
            billed_paise=acc.billed_paise,
            collected_paise=acc.collected_paise,
            outstanding_paise=acc.billed_paise - acc.collected_paise,
            refunds_paise=acc.refunds_paise,
        )
        for mode, acc in accumulators.items()
    ]

    billed_paise = sum(acc.billed_paise for acc in accumulators.values())
    collected_paise = sum(acc.collected_paise for acc in accumulators.values())
    refunds_paise = sum(acc.refunds_paise for acc in accumulators.values())

    return ReconciliationReport(
        billed_paise=billed_paise,
        collected_paise=collected_paise,
        outstanding_paise=billed_paise - collected_paise,
        refunds_paise=refunds_paise,
        payment_mode_breakdown=payment_mode_breakdown,
    )
