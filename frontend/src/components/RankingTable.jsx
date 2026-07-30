export default function RankingTable({ title, rows, valueLabel, formatValue }) {
  return (
    <div className="panel">
      <h3 className="panel__title">{title}</h3>
      {rows.length === 0 ? (
        <p className="muted">No medicines to rank.</p>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Medicine</th>
                <th className="num">{valueLabel}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={row.drug_name}>
                  <td className="num tabular">{i + 1}</td>
                  <td>{row.drug_name}</td>
                  <td className="num tabular">{formatValue(row)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
