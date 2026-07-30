import { Navigate, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import { BillingLogProvider } from "./context/BillingLogContext";
import Analytics from "./pages/Analytics";
import Narrative from "./pages/Narrative";
import Reconciliation from "./pages/Reconciliation";

export default function App() {
  return (
    <BillingLogProvider>
      <div className="app-shell">
        <Sidebar />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Navigate to="/reconciliation" replace />} />
            <Route path="/reconciliation" element={<Reconciliation />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/narrative" element={<Narrative />} />
            <Route path="*" element={<Navigate to="/reconciliation" replace />} />
          </Routes>
        </main>
      </div>
    </BillingLogProvider>
  );
}
