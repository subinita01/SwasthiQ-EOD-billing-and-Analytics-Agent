# SwasthiQ EOD Billing & Analytics Agent

See [REFERENCE.md](./REFERENCE.md) for the full assignment spec (hard constraints, billing log schema, required screens, grading priorities). See [CLAUDE.md](./CLAUDE.md) for implementation-level detail on every module. This file covers setup, the REST API contract, and how the pipeline keeps the AI narrative grounded in the deterministic reports.

## Getting started with Claude Code

```bash
npm install -g @anthropic-ai/claude-code
cd swasthiq-eod-agent
claude
```

## Project layout

```
backend/
  app/
    models/      # Pydantic schemas: billing.py (input), report.py (reports), narrative.py
    services/    # validation.py, reconciliation.py, analytics.py, narrative.py
    routers/     # billing.py, reconciliation.py, analytics.py, report.py, narrative.py
    tests/
  sample_data/   # 3 synthetic clinic-day billing logs (see CLAUDE.md)
  requirements.txt
frontend/
  src/
    components/  # Sidebar, StatCard, PaymentTable, RevenueChart, TracedFigures, ErrorState, RankingTable
    pages/       # Reconciliation.jsx, Analytics.jsx, Narrative.jsx
    context/     # BillingLogContext.jsx
```

## Running the backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # .venv/bin/python on macOS/Linux
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

Run tests: `cd backend && .venv/Scripts/python -m pytest app/tests/ -v`

### Environment variables (backend, `backend/.env`)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GROQ_API_KEY` | For `/narrative` to actually call a model | — | Free key from [console.groq.com](https://console.groq.com). Without it, `/narrative` still returns `200` with `generation_error` explaining it's unavailable — it never 500s or blocks the other endpoints. |
| `NARRATIVE_MODEL` | No | `llama-3.3-70b-versatile` | Groq model id used for the narrative summary. |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173` | Comma-separated list of origins allowed to call the API from a browser. |

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173`, calling the backend at `VITE_API_BASE_URL` (`frontend/.env`, default `http://localhost:8000`). Load a billing log via the sidebar: upload a JSON file, or click one of the "Sample: Day N" buttons to load the same fixtures the backend test suite uses.

## API contract

Base URL: `http://localhost:8000` (or whatever `VITE_API_BASE_URL` points at). All endpoints below are `POST` and take the **raw billing log as the entire request body** — a bare JSON array of rows, not wrapped in an envelope object:

```json
[
  {
    "clinic_id": "clinic-1",
    "visit_id": "visit-1",
    "timestamp": "2026-07-28T09:15:00Z",
    "doctor_id": "doc-1",
    "line_items": [
      { "drug_name": "Paracetamol", "qty": 2, "unit_price_paise": 500 }
    ],
    "payment_mode": "cash",
    "amount_paid_paise": 1000,
    "discount_paise": 0,
    "is_refund": false
  }
]
```

All money fields are **integer paise**. `timestamp` must be ISO 8601 UTC (`Z` or `+00:00`). `payment_mode` is one of `cash | card | upi`. `amount_paid_paise` must be `<= 0` when `is_refund` is `true`, and `>= 0` otherwise. Every row in one log must share the same `clinic_id` — a log is one clinic's daily billing log, and every report aggregates across all rows with no per-clinic grouping, so a mixed-clinic payload is rejected rather than silently blended into one report. See `backend/app/models/billing.py` for the full schema.

| Endpoint | Returns | Notes |
|---|---|---|
| `GET /health` | `{"status": "ok"}` | Liveness check. |
| `POST /billing-log/validate` | `{"valid_row_count": <int>}` | Validates only; doesn't compute anything. |
| `POST /reconciliation` | `ReconciliationReport` | Billed/collected/outstanding/refunds, totals + per payment mode. |
| `POST /analytics` | `AnalyticsReport` | Revenue by hour, peak hour, medicine rankings. |
| `POST /report` | `EODReport` = `{reconciliation, analytics}` | Validates the log once, returns both — for a dashboard that needs both without submitting the log twice. |
| `POST /narrative` | `NarrativeSummary` | AI narrative + citation-checked "traced figures". Always `200` if the log itself is valid (see below). |

### `POST /reconciliation`

```json
{
  "billed_paise": 7450,
  "collected_paise": 6750,
  "outstanding_paise": 700,
  "refunds_paise": 500,
  "payment_mode_breakdown": [
    { "payment_mode": "cash", "transaction_count": 2, "billed_paise": 1000, "collected_paise": 1000, "outstanding_paise": 0, "refunds_paise": 500 },
    { "payment_mode": "card", "transaction_count": 2, "billed_paise": 4300, "collected_paise": 4300, "outstanding_paise": 0, "refunds_paise": 0 },
    { "payment_mode": "upi",  "transaction_count": 2, "billed_paise": 2150, "collected_paise": 1450, "outstanding_paise": 700, "refunds_paise": 0 }
  ]
}
```

`payment_mode_breakdown` always has exactly 3 entries (cash/card/upi), zero-filled for a mode that saw no transactions that day. Per-mode values sum exactly to the top-level totals (asserted in tests).

### `POST /analytics`

```json
{
  "revenue_by_hour": [
    { "hour": 0, "revenue_paise": 0 },
    { "hour": 9, "revenue_paise": 2300 },
    { "hour": 11, "revenue_paise": -500 },
    { "hour": 14, "revenue_paise": 3450 }
  ],
  "peak_hour": 14,
  "top_medicines_by_quantity": [
    { "drug_name": "Bandage", "net_qty": 7 },
    { "drug_name": "Paracetamol", "net_qty": 4 }
  ],
  "top_medicines_by_revenue": [
    { "drug_name": "Cough Syrup", "net_revenue_paise": 4500 },
    { "drug_name": "Paracetamol", "net_revenue_paise": 2000 }
  ],
  "notes": [
    "Per-medicine revenue is derived from line-item qty * unit_price_paise and is gross of discount: discount_paise is recorded per visit, not allocated to individual line items, so a true post-discount revenue per medicine cannot be computed from this schema."
  ]
}
```

`revenue_by_hour` always has all 24 hours (zero-filled); `peak_hour` is `null` for an empty log. Revenue can be negative in an hour dominated by refunds. The two medicine rankings are independent orderings — the top item by quantity is not necessarily the top item by revenue (see clinic_day_1: Bandage tops quantity, Cough Syrup tops revenue). `notes` states plainly when a figure can't be computed exactly from the schema, rather than approximating it silently.

### `POST /narrative`

```json
{
  "narrative": "The peak hour of the day was 14. Revenue for the day included 3450 paise at the peak hour, 2300 paise at hour 9, and 1000 paise at hour 10, although there was a loss of 500 paise at hour 11. The clinic sold 7 Bandages, 3 Cough Syrups, and 4 Paracetamols. The total billed amount was ₹74.50 and the total collected amount was ₹67.50, with ₹7.00 outstanding. ...",
  "traced_figures": [
    { "field": "analytics.peak_hour", "value": 14, "displayed_text": "14", "verified": true, "issues": [] },
    { "field": "analytics.revenue_by_hour.14.revenue_paise", "value": 3450, "displayed_text": "3450", "verified": true, "issues": [] },
    {
      "field": "analytics.revenue_by_hour.11.revenue_paise",
      "value": -500,
      "displayed_text": "500",
      "verified": false,
      "issues": ["displayed_text '500' resolves to 500, not the cited value -500"]
    }
  ],
  "fully_verified": false,
  "generation_error": null
}
```

This is a real response captured against `sample_data/clinic_day_1.json` — not a hypothetical. It's a good example of the validator actually catching something: the model described hour 11 in prose as "a loss of 500 paise" (correct in spirit) but declared the citation's `displayed_text` as `"500"` without the sign, while claiming `value: -500`. Those two don't numerically agree, so that one citation is flagged `verified: false` and the whole response is `fully_verified: false` — even though every other figure in the same response checked out. Nothing is hidden or silently corrected; the frontend's "Traced Figures" panel shows exactly which claims to distrust. See **Data consistency** below for how this check works.

If `GROQ_API_KEY` isn't set, or the model call fails, or the model returns unparseable output, `/narrative` still responds `200`:

```json
{
  "narrative": "AI narrative summary is unavailable right now.",
  "traced_figures": [],
  "fully_verified": false,
  "generation_error": "RuntimeError: GROQ_API_KEY environment variable is not set"
}
```

### Error responses

Every endpoint uses **one consistent shape** for malformed input — a `422` with a per-row, per-field breakdown — regardless of whether the whole payload was the wrong shape or just one field on one row was bad:

```json
{
  "detail": "2 invalid row(s) in billing log",
  "errors": [
    { "row_index": 0, "field": "visit_id", "message": "Field required", "invalid_value": { "...": "the full row" } },
    { "row_index": 0, "field": "line_items.0.qty", "message": "Input should be greater than 0", "invalid_value": -1 }
  ]
}
```

`row_index: -1` means the problem is with the payload as a whole (e.g. `"Billing log must be a JSON array of rows"`), not a specific row. This is deliberate: every `POST` body is typed `rows: Any` rather than `list[dict]`, so *all* shape validation — not just per-row content — routes through the same validator and error format, instead of FastAPI's separately-shaped default `422` kicking in for a malformed top-level payload.

## Data consistency: keeping the narrative grounded in the reports

The hard constraint driving this design (see REFERENCE.md): the narrative may only state numbers that exist in the deterministic report, and every cited number must be checked programmatically — never just trusted because the prompt asked nicely.

```
billing log (raw JSON)
        │
        ▼
parse_billing_log()  ── malformed row/shape ──▶ 422, same shape everywhere
        │
        ▼
BillingLogEntry[]  (validated, typed, integer-paise)
        │
        ├──▶ build_reconciliation_report() ──▶ ReconciliationReport   ┐
        │                                                              │  100% deterministic.
        └──▶ build_analytics_report()      ──▶ AnalyticsReport        ┘  No LLM involved at all.
                        │
                        ▼
        build_figure_index(reconciliation, analytics)
        → flat {"dotted.field.path": value} map of every number
          in both reports - the *only* numbers the model may cite.
        → nothing in this index is invented; it's read straight
          off the report models above.
                        │
                        ▼
        prompt: the figure index, verbatim, plus instructions to
        cite only from it, state plainly when something (e.g.
        profit) isn't in it, and declare a citation for every
        number it writes
                        │
                        ▼
                 GroqLLMClient.complete()
                        │
                        ▼
        LLM response: {"narrative": "...", "citations": [...]}
                        │
                        ▼
              citation validator (two independent checks)
```

The validator does not trust the model's self-report. Two checks, both required for `fully_verified: true`:

1. **Per citation** — for every `{field, value, displayed_text}` the model declared: does `field` exist in the figure index? Does `value` equal the report's actual value at that field, exactly? Does `displayed_text` (e.g. `"₹74.50"`) numerically resolve back to that same `value` (rupees-with-decimal → ×100 paise, otherwise parsed as-is)?
2. **Narrative-wide sweep** — every number-looking token actually written in the narrative text (a regex that skips digits fused into IDs like `visit-1`) must be covered by some citation's exact `displayed_text`. This is what catches a number the model wrote in prose but never declared as a citation at all — a hallucination that per-citation checking alone would miss entirely, since there'd be no citation to check.

Every check becomes one `TracedFigure` (`field`, `value`, `displayed_text`, `verified`, `issues`) — including synthetic `field: "<uncited>"` entries for narrative-wide-sweep failures — which the frontend renders as the "Traced Figures" panel. A response is `fully_verified` only if every single check passes; a single bad citation (like the hour-11 example above) flips the whole response to `fully_verified: false` while still showing exactly which figures are trustworthy and which aren't.

Malformed model output — invalid JSON, a markdown-fenced response, a missing/wrong-typed field, a network error, or the LLM client failing to even construct (e.g. no API key) — never crashes this pipeline. It's caught and degraded to a safe fallback `NarrativeSummary` with `generation_error` set, so `/narrative` has exactly one response shape regardless of what went wrong upstream. See `backend/app/services/narrative.py` and `CLAUDE.md` for the implementation.
