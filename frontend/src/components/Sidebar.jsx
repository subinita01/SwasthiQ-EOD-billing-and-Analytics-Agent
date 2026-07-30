import { useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import { useBillingLog } from "../context/BillingLogContext";

const SAMPLE_DAYS = [
  { file: "clinic_day_1.json", label: "Sample: Day 1" },
  { file: "clinic_day_2.json", label: "Sample: Day 2" },
  { file: "clinic_day_3.json", label: "Sample: Day 3" },
];

const NAV_ITEMS = [
  { to: "/reconciliation", label: "Reconciliation" },
  { to: "/analytics", label: "Analytics" },
  { to: "/narrative", label: "AI Narrative" },
];

export default function Sidebar() {
  const { rows, source, setRows } = useBillingLog();
  const [loadError, setLoadError] = useState(null);
  const fileInputRef = useRef(null);

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      if (!Array.isArray(parsed)) {
        setLoadError(`"${file.name}" must be a JSON array of billing log rows.`);
        return;
      }
      setLoadError(null);
      setRows(parsed, file.name);
    } catch {
      setLoadError(`"${file.name}" is not valid JSON.`);
    }
  }

  async function handleSampleLoad(sample) {
    try {
      const response = await fetch(`/sample-data/${sample.file}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const parsed = await response.json();
      if (!Array.isArray(parsed)) {
        setLoadError(`${sample.label} did not return a JSON array.`);
        return;
      }
      setLoadError(null);
      setRows(parsed, sample.label);
    } catch {
      setLoadError(`Could not load ${sample.label}.`);
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">SwasthiQ EOD Agent</div>

      <nav className="sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `sidebar__link${isActive ? " is-active" : ""}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar__section">
        <h4 className="sidebar__heading">Billing log</h4>

        {rows ? (
          <p className="sidebar__status sidebar__status--loaded">
            Loaded: {source ?? "unnamed"} ({rows.length} row{rows.length === 1 ? "" : "s"})
          </p>
        ) : (
          <p className="sidebar__status">No billing log loaded yet.</p>
        )}

        <button
          type="button"
          className="button button--full"
          onClick={() => fileInputRef.current?.click()}
        >
          Upload JSON file
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/json"
          onChange={handleFileChange}
          hidden
        />

        <div className="sidebar__samples">
          {SAMPLE_DAYS.map((sample) => (
            <button
              key={sample.file}
              type="button"
              className="button button--ghost button--full"
              onClick={() => handleSampleLoad(sample)}
            >
              {sample.label}
            </button>
          ))}
        </div>

        {loadError && <p className="sidebar__error">{loadError}</p>}
      </div>
    </aside>
  );
}
