import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import { T } from "../styles/theme.js";
import Btn from "../components/ui/Btn.jsx";

export default function Home() {
  const { user, status } = useAuth();
  const authenticated = status === "authenticated" && user;

  if (authenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div
      className="route-fade"
      style={{
        height: "100%",
        background: T.bg,
        color: T.tx,
        fontFamily: T.fB,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 24px",
        overflowY: "auto",
      }}
    >
      <div style={{ maxWidth: 520, textAlign: "center" }}>
        <div
          style={{
            fontFamily: T.fH,
            fontSize: 28,
            fontWeight: 700,
            letterSpacing: "-0.8px",
            marginBottom: 8,
          }}
        >
          <span style={{ color: T.ac }}>C</span>ompetizione
        </div>
        <div
          style={{
            fontFamily: T.fM,
            fontSize: 10,
            letterSpacing: 1.2,
            textTransform: "uppercase",
            color: T.tx3,
            marginBottom: 28,
          }}
        >
          ESPORTS · ANALYTICS
        </div>
        <h1
          style={{
            fontFamily: T.fH,
            fontSize: 32,
            fontWeight: 700,
            letterSpacing: "-1px",
            lineHeight: 1.15,
            marginBottom: 14,
          }}
        >
          Compite. Mejora. Domina.
        </h1>
        <p style={{ color: T.tx2, fontSize: 14, lineHeight: 1.6, marginBottom: 24 }}>
          La plataforma para organizar torneos 1v1 con calendario automático, clasificación
          en tiempo real y avance instantáneo de rondas.
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
          <Link to="/login" style={{ textDecoration: "none" }}>
            <Btn>Iniciar sesión</Btn>
          </Link>
          <Link to="/register" style={{ textDecoration: "none" }}>
            <Btn variant="ghost">Crear cuenta</Btn>
          </Link>
        </div>
      </div>
    </div>
  );
}
