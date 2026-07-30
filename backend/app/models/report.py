from __future__ import annotations

from pydantic import BaseModel

from app.models.billing import PaymentMode


class PaymentModeBreakdown(BaseModel):
    payment_mode: PaymentMode
    transaction_count: int
    billed_paise: int
    collected_paise: int
    outstanding_paise: int
    refunds_paise: int


class ReconciliationReport(BaseModel):
    billed_paise: int
    collected_paise: int
    outstanding_paise: int
    refunds_paise: int
    payment_mode_breakdown: list[PaymentModeBreakdown]


class HourlyRevenue(BaseModel):
    hour: int
    revenue_paise: int


class MedicineQuantityRanking(BaseModel):
    drug_name: str
    net_qty: int


class MedicineRevenueRanking(BaseModel):
    drug_name: str
    net_revenue_paise: int


class AnalyticsReport(BaseModel):
    revenue_by_hour: list[HourlyRevenue]
    peak_hour: int | None
    top_medicines_by_quantity: list[MedicineQuantityRanking]
    top_medicines_by_revenue: list[MedicineRevenueRanking]
    notes: list[str]


class EODReport(BaseModel):
    reconciliation: ReconciliationReport
    analytics: AnalyticsReport
