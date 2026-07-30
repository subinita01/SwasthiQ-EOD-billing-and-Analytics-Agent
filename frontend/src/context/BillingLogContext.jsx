import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { ApiValidationError, fetchAnalytics, fetchNarrative, fetchReconciliation } from "../api";

const BillingLogContext = createContext(null);

const EMPTY_REQUEST_STATE = { data: null, loading: false, error: null };

function useRequestSlice(rows, fetcher) {
  const [state, setState] = useState(EMPTY_REQUEST_STATE);

  const load = useCallback(
    async ({ force = false } = {}) => {
      if (!rows) return;
      if (state.loading) return;
      if (state.data && !force) return;

      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const data = await fetcher(rows);
        setState({ data, loading: false, error: null });
      } catch (error) {
        setState({ data: null, loading: false, error });
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [rows, state.loading, state.data],
  );

  const reset = useCallback(() => setState(EMPTY_REQUEST_STATE), []);

  return [state, load, reset];
}

export function BillingLogProvider({ children }) {
  const [rows, setRowsState] = useState(null);
  const [source, setSource] = useState(null);

  const [reconciliation, loadReconciliation, resetReconciliation] = useRequestSlice(
    rows,
    fetchReconciliation,
  );
  const [analytics, loadAnalytics, resetAnalytics] = useRequestSlice(rows, fetchAnalytics);
  const [narrative, loadNarrative, resetNarrative] = useRequestSlice(rows, fetchNarrative);

  const setRows = useCallback(
    (newRows, newSource) => {
      setRowsState(newRows);
      setSource(newSource ?? null);
      resetReconciliation();
      resetAnalytics();
      resetNarrative();
    },
    [resetReconciliation, resetAnalytics, resetNarrative],
  );

  const value = useMemo(
    () => ({
      rows,
      source,
      setRows,
      reconciliation,
      loadReconciliation,
      analytics,
      loadAnalytics,
      narrative,
      loadNarrative,
    }),
    [
      rows,
      source,
      setRows,
      reconciliation,
      loadReconciliation,
      analytics,
      loadAnalytics,
      narrative,
      loadNarrative,
    ],
  );

  return <BillingLogContext.Provider value={value}>{children}</BillingLogContext.Provider>;
}

export function useBillingLog() {
  const ctx = useContext(BillingLogContext);
  if (!ctx) {
    throw new Error("useBillingLog must be used within a BillingLogProvider");
  }
  return ctx;
}

export { ApiValidationError };
