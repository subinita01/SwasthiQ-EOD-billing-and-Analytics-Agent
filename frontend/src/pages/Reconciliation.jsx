import { useEffect } from "react";
import ErrorState from "../components/ErrorState";
import PaymentTable from "../components/PaymentTable";
import StatCard from "../components/StatCard";
import { useBillingLog } from "../context/BillingLogContext";
import { formatPaise } from "../utils/format";

export default function Reconciliation() {
  const { rows, reconciliation, loadReconciliation } = useBillingLog();

  useEffect(() => {
    if (rows) loadReconciliation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows]);

  if (!rows) {
    return (
      <div className="empty-state">
        <h2>EOD Reconciliation</h2>
        <p>Upload a billing log or load a sample day from the sidebar to see today's numbers.</p>
      </div>
    );
  }

  const { data, loading, error } = reconciliation;

  return (
    <div className="page">
      <h2 className="page__title">EOD Reconciliation</h2>

      {loading && <p className="muted">Computing reconciliation report…</p>}
      <ErrorState error={error} onRetry={() => loadReconciliation({ force: true })} />

      {data && (
        <>
          <div className="stat-grid">
            <StatCard label="Billed" value={formatPaise(data.billed_paise)} tone="neutral" />
            <StatCard label="Collected" value={formatPaise(data.collected_paise)} tone="good" />
            <StatCard
              label="Outstanding"
              value={formatPaise(data.outstanding_paise)}
              tone={data.outstanding_paise > 0 ? "warning" : "neutral"}
            />
            <StatCard label="Refunds" value={formatPaise(data.refunds_paise)} tone="critical" />
          </div>

          <PaymentTable breakdown={data.payment_mode_breakdown} />
        </>
      )}
    </div>
  );
}
