import { useEffect } from "react";
import ErrorState from "../components/ErrorState";
import TracedFigures from "../components/TracedFigures";
import { useBillingLog } from "../context/BillingLogContext";

export default function Narrative() {
  const { rows, narrative, loadNarrative } = useBillingLog();

  useEffect(() => {
    if (rows) loadNarrative();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows]);

  if (!rows) {
    return (
      <div className="empty-state">
        <h2>AI Narrative Summary</h2>
        <p>Upload a billing log or load a sample day from the sidebar to generate a summary.</p>
      </div>
    );
  }

  const { data, loading, error } = narrative;

  return (
    <div className="page">
      <h2 className="page__title">AI Narrative Summary</h2>

      {loading && <p className="muted">Generating narrative summary… this can take a few seconds.</p>}
      <ErrorState error={error} onRetry={() => loadNarrative({ force: true })} />

      {data && data.generation_error && (
        <div className="banner banner--critical" role="alert">
          AI narrative summary is unavailable: {data.generation_error}
        </div>
      )}

      {data && !data.generation_error && (
        <>
          {data.fully_verified ? (
            <div className="banner banner--good">
              Every figure in this narrative was verified against the reconciliation and
              analytics reports.
            </div>
          ) : (
            <div className="banner banner--warning" role="alert">
              One or more figures in this narrative could not be verified against the report.
              Check the Traced Figures panel below before trusting it.
            </div>
          )}

          <div className="panel narrative-text">
            {data.narrative.split("\n\n").map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))}
          </div>

          <TracedFigures figures={data.traced_figures} />
        </>
      )}
    </div>
  );
}
