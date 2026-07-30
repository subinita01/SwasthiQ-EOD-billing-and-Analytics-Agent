import { ApiValidationError } from "../context/BillingLogContext";

const MAX_VALUE_PREVIEW_LENGTH = 60;

// For a "field required" error the backend has no specific bad value to
// point at, so invalid_value is the *entire* row object - stringified
// raw, that would dominate the table with an unreadable blob for what is
// likely the single most common error type. Truncate for a preview;
// row_index + field already say where and what, this is just context.
function formatInvalidValue(value) {
  const str = JSON.stringify(value);
  if (str === undefined) return "";
  return str.length > MAX_VALUE_PREVIEW_LENGTH
    ? `${str.slice(0, MAX_VALUE_PREVIEW_LENGTH)}…`
    : str;
}

export default function ErrorState({ error, onRetry }) {
  if (!error) return null;

  if (error instanceof ApiValidationError) {
    return (
      <div className="panel error-panel" role="alert">
        <p className="error-panel__heading">{error.message}</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Row</th>
                <th>Field</th>
                <th>Problem</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {error.errors.map((e, i) => (
                <tr key={i}>
                  <td className="num">{e.row_index}</td>
                  <td>{e.field}</td>
                  <td>{e.message}</td>
                  <td>
                    <code>{formatInvalidValue(e.invalid_value)}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {onRetry && (
          <button type="button" className="button" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="panel error-panel" role="alert">
      <p className="error-panel__heading">{error.message}</p>
      {onRetry && (
        <button type="button" className="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
