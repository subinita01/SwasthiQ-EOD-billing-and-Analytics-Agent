const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Mirrors backend BillingLogValidationError.to_dict(): {"detail": str, "errors": [...]}.
// Every /reconciliation, /analytics, /narrative, /report, /billing-log/validate
// endpoint returns this exact shape on a 422, regardless of whether the whole
// payload was malformed (wrong top level shape) or just one row/field was.
export class ApiValidationError extends Error {
  constructor(detail, errors) {
    super(detail);
    this.name = "ApiValidationError";
    this.errors = errors ?? [];
  }
}

async function postBillingLog(path, rows) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rows),
    });
  } catch {
    throw new Error(
      `Could not reach the backend at ${API_BASE_URL}. Is it running (uvicorn app.main:app --reload)?`,
    );
  }

  if (response.status === 422) {
    const body = await response.json();
    throw new ApiValidationError(body.detail, body.errors);
  }
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }
  return response.json();
}

export const fetchReconciliation = (rows) => postBillingLog("/reconciliation", rows);
export const fetchAnalytics = (rows) => postBillingLog("/analytics", rows);
export const fetchNarrative = (rows) => postBillingLog("/narrative", rows);
