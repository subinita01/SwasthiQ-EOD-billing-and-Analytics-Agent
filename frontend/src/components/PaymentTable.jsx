import { formatPaise } from "../utils/format";

const MODE_LABELS = { cash: "Cash", card: "Card", upi: "UPI" };

export default function PaymentTable({ breakdown }) {
  return (
    <div className="panel">
      <h3 className="panel__title">Breakdown by payment mode</h3>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Mode</th>
              <th className="num">Transactions</th>
              <th className="num">Billed</th>
              <th className="num">Collected</th>
              <th className="num">Outstanding</th>
              <th className="num">Refunds</th>
            </tr>
          </thead>
          <tbody>
            {breakdown.map((row) => (
              <tr key={row.payment_mode}>
                <td>{MODE_LABELS[row.payment_mode] ?? row.payment_mode}</td>
                <td className="num tabular">{row.transaction_count}</td>
                <td className="num tabular">{formatPaise(row.billed_paise)}</td>
                <td className="num tabular">{formatPaise(row.collected_paise)}</td>
                <td className="num tabular">{formatPaise(row.outstanding_paise)}</td>
                <td className="num tabular">{formatPaise(row.refunds_paise)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
