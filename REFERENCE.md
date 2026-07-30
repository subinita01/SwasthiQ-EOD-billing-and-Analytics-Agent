# SwasthiQ EOD Billing & Analytics Agent

## What this is
A take-home assignment. Python REST API + React frontend that processes
a clinic's daily billing log into (1) deterministic reconciliation,
(2) analytics, (3) LLM narrative summary grounded in (1) and (2).

## Hard constraints — do not violate
- The deterministic layer (reconciliation + analytics) NEVER calls an LLM.
  It is ground truth. All money is integer paise, never float rupees.
- The narrative layer must cite ONLY numbers that exist in the deterministic
  report. Every figure in the narrative must be verifiable against the report
  programmatically (not just "trust the prompt") — build an explicit
  validation step that checks each cited number against report fields.
- If a metric can't be computed from given data (e.g. profit — no cost price
  in schema), the narrative must say so plainly, not approximate or invent it.
- Malformed LLM output must be handled gracefully — no crash, no silent
  corruption of the response.
- Malformed input rows must return a specific actionable validation error,
  not a generic 500.
- Storage: SQLite or in-memory only.

## Stack
- Backend: Python (FastAPI), Pydantic for schema validation, pytest for tests
- Frontend: React
- LLM: [pick one — Anthropic/OpenAI, using env var for API key]

## Billing log schema
clinic_id (str), visit_id (str), timestamp (ISO8601 UTC), doctor_id (str,
unused), line_items ([{drug_name, qty, unit_price_paise}]),
payment_mode (cash|card|upi), amount_paid_paise (int, negative if refund),
discount_paise (int), is_refund (bool)

## Three screens required (React)
1. EOD Reconciliation Dashboard — stat cards (billed/collected/outstanding/
   refunds) + payment-mode breakdown table
2. Analytics — revenue-by-hour bar chart with peak hour called out, plus
   two DISTINCT rankings: top medicines by quantity, top medicines by revenue
3. AI Narrative Summary — generated text + "Traced Figures" panel mapping
   every cited number to its source field in the report
Shared sidebar nav persists across all three.

## Grading priorities (in order)
1. Correctness of deterministic reconciliation/analytics
2. Every narrative number matches the report exactly (auto-graded)
3. UI matches the 3 screens structurally
4. Code structure, error handling, test coverage
5. Edge case handling in sample dataset
