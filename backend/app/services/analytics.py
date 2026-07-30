from __future__ import annotations

from collections import defaultdict

from app.models.billing import BillingLogEntry
from app.models.report import (
    AnalyticsReport,
    HourlyRevenue,
    MedicineQuantityRanking,
    MedicineRevenueRanking,
)

MEDICINE_REVENUE_DISCOUNT_NOTE = (
    "Per-medicine revenue is derived from line-item qty * unit_price_paise "
    "and is gross of discount: discount_paise is recorded per visit, not "
    "allocated to individual line items, so a true post-discount revenue "
    "per medicine cannot be computed from this schema."
)


def build_analytics_report(entries: list[BillingLogEntry]) -> AnalyticsReport:
    """Build the analytics report: revenue by hour-of-day (UTC) and two
    distinct medicine rankings (by net quantity, by net line-item revenue).

    Refund rows subtract from both quantity and revenue for the medicines
    they return, so a heavily-refunded drug can rank low or even go
    negative rather than being silently excluded.
    """
    hourly_revenue: dict[int, int] = defaultdict(int)
    qty_by_drug: dict[str, int] = defaultdict(int)
    revenue_by_drug: dict[str, int] = defaultdict(int)

    for entry in entries:
        hourly_revenue[entry.timestamp.hour] += entry.amount_paid_paise

        sign = -1 if entry.is_refund else 1
        for item in entry.line_items:
            qty_by_drug[item.drug_name] += sign * item.qty
            revenue_by_drug[item.drug_name] += sign * item.qty * item.unit_price_paise

    revenue_by_hour = [
        HourlyRevenue(hour=hour, revenue_paise=hourly_revenue.get(hour, 0))
        for hour in range(24)
    ]

    peak_hour = max(hourly_revenue, key=hourly_revenue.get) if hourly_revenue else None

    top_medicines_by_quantity = sorted(
        (
            MedicineQuantityRanking(drug_name=name, net_qty=qty)
            for name, qty in qty_by_drug.items()
        ),
        key=lambda ranking: ranking.net_qty,
        reverse=True,
    )
    top_medicines_by_revenue = sorted(
        (
            MedicineRevenueRanking(drug_name=name, net_revenue_paise=revenue)
            for name, revenue in revenue_by_drug.items()
        ),
        key=lambda ranking: ranking.net_revenue_paise,
        reverse=True,
    )

    notes = [MEDICINE_REVENUE_DISCOUNT_NOTE] if revenue_by_drug else []

    return AnalyticsReport(
        revenue_by_hour=revenue_by_hour,
        peak_hour=peak_hour,
        top_medicines_by_quantity=top_medicines_by_quantity,
        top_medicines_by_revenue=top_medicines_by_revenue,
        notes=notes,
    )
