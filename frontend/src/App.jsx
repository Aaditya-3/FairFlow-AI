import { Toaster } from "react-hot-toast";
import { Navigate, Route, Routes } from "react-router-dom";

import { TOKEN_STORAGE_KEY } from "./api/fairlensApi";
import ProtectedLayout from "./layouts/ProtectedLayout";
import Audit from "./pages/Audit";
import Candidates from "./pages/Candidates";
import Dashboard from "./pages/Dashboard";
import LoginPage from "./pages/LoginPage";
import Mitigate from "./pages/Mitigate";
import RegisterPage from "./pages/RegisterPage";

function ProtectedRoutes() {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  return token ? <ProtectedLayout /> : <Navigate to="/login" replace />;
}

function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            borderRadius: "18px",
            background: "#0f172a",
            color: "#ffffff"
          }
        }}
      />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route element={<ProtectedRoutes />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/candidates/:auditId" element={<Candidates />} />
          <Route path="/mitigate/:auditId" element={<Mitigate />} />
        </Route>
      </Routes>
    </>
  );
}

export default App;
