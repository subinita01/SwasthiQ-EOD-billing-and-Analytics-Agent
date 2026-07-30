import { useEffect } from "react";
import ErrorState from "../components/ErrorState";
import RankingTable from "../components/RankingTable";
import RevenueChart from "../components/RevenueChart";
import { useBillingLog } from "../context/BillingLogContext";
import { formatPaise } from "../utils/format";

export default function Analytics() {
  const { rows, analytics, loadAnalytics } = useBillingLog();

  useEffect(() => {
    if (rows) loadAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows]);

  if (!rows) {
    return (
      <div className="empty-state">
        <h2>Analytics</h2>
        <p>Upload a billing log or load a sample day from the sidebar to see analytics.</p>
      </div>
    );
  }

  const { data, loading, error } = analytics;

  return (
    <div className="page">
      <h2 className="page__title">Analytics</h2>

      {loading && <p className="muted">Computing analytics…</p>}
      <ErrorState error={error} onRetry={() => loadAnalytics({ force: true })} />

      {data && (
        <>
          <RevenueChart hourly={data.revenue_by_hour} peakHour={data.peak_hour} />

          <div className="two-column">
            <RankingTable
              title="Top medicines by quantity"
              rows={data.top_medicines_by_quantity}
              valueLabel="Net qty"
              formatValue={(row) => row.net_qty}
            />
            <RankingTable
              title="Top medicines by revenue"
              rows={data.top_medicines_by_revenue}
              valueLabel="Net revenue"
              formatValue={(row) => formatPaise(row.net_revenue_paise)}
            />
          </div>

          {data.notes.length > 0 && (
            <div className="panel notes-panel">
              {data.notes.map((note, i) => (
                <p key={i} className="muted">
                  {note}
                </p>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
