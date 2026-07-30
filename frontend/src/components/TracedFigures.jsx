export default function TracedFigures({ figures }) {
  if (figures.length === 0) {
    return (
      <div className="panel">
        <h3 className="panel__title">Traced figures</h3>
        <p className="muted">The narrative didn't cite any figures from the report.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h3 className="panel__title">Traced figures</h3>
      <p className="muted">
        Every number in the narrative, mapped back to the report field it came from.
      </p>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>As written</th>
              <th>Source field</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {figures.map((fig, i) => (
              <tr key={i} className={fig.verified ? "is-verified" : "is-unverified"}>
                <td>
                  <span className={`badge ${fig.verified ? "badge--good" : "badge--critical"}`}>
                    {fig.verified ? "Verified" : "Unverified"}
                  </span>
                </td>
                <td className="tabular">{fig.displayed_text}</td>
                <td>{fig.field === "<uncited>" ? <em>no citation</em> : <code>{fig.field}</code>}</td>
                <td>
                  {fig.issues.length > 0 && (
                    <ul className="issue-list">
                      {fig.issues.map((issue, j) => (
                        <li key={j}>{issue}</li>
                      ))}
                    </ul>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
