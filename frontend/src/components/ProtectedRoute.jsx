import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";

export default function ProtectedRoute({ children }) {
  const { status } = useAuth();

  if (status === "loading") {
    return <p>Cargando…</p>;
  }
  if (status === "anonymous") {
    return <Navigate to="/login" replace />;
  }
  return children;
}
