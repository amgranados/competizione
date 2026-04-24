import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import { T } from "../styles/theme.js";
import Btn from "../components/ui/Btn.jsx";
import Icon from "../components/ui/Icon.jsx";

export default function Home() {
  const { user, status, logout } = useAuth();
  const authenticated = status === "authenticated" && user;

  return (
    <div
      className="route-fade"
      style={{
        display: "flex",
        height: "100%",
        background: T.bg,
        color: T.tx,
        fontFamily: T.fB,
      }}
    >
      <Sidebar user={user} authenticated={authenticated} onLogout={logout} />

      <section style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <header style={{ padding: "22px 28px 0" }}>
          <h1
            style={{
              fontFamily: T.fH,
              fontSize: 28,
              fontWeight: 700,
              letterSpacing: "-0.8px",
              marginBottom: 4,
            }}
          >
            Dashboard
          </h1>
          <p style={{ fontFamily: T.fM, fontSize: 10, letterSpacing: 1.2, textTransform: "uppercase", color: T.tx3 }}>
            {authenticated ? `Bienvenido, ${user.nickname}` : "No has iniciado sesión"}
          </p>
        </header>

        <div style={{ padding: "20px 28px 28px", overflowY: "auto", flex: 1 }}>
          {authenticated ? <AuthenticatedHome user={user} /> : <AnonymousHome />}
        </div>
      </section>
    </div>
  );
}

function Sidebar({ user, authenticated, onLogout }) {
  return (
    <aside
      style={{
        width: 220,
        flexShrink: 0,
        background: T.s1,
        borderRight: `1px solid ${T.bd}`,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ padding: "26px 22px 24px" }}>
        <div
          style={{
            fontFamily: T.fH,
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: "-0.6px",
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
            marginTop: 4,
          }}
        >
          ESPORTS · ANALYTICS
        </div>
      </div>

      <nav style={{ flex: 1 }}>
        <SidebarItem label="Dashboard" active />
        <SidebarItem label="Torneos" />
        <SidebarItem label="Equipos" />
        <SidebarItem label="Estadísticas" />
      </nav>

      {authenticated && (
        <div
          style={{
            padding: "14px 22px",
            borderTop: `1px solid ${T.bd}`,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <Avatar name={user.nickname} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontFamily: T.fB,
                fontSize: 12,
                fontWeight: 600,
                color: T.tx,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {user.nickname}
            </div>
            <div
              style={{
                fontFamily: T.fM,
                fontSize: 10,
                color: T.tx3,
                letterSpacing: 1,
              }}
            >
              UNRANKED
            </div>
          </div>
          <button
            onClick={onLogout}
            aria-label="Cerrar sesión"
            style={{
              background: "transparent",
              border: "none",
              color: T.tx2,
              cursor: "pointer",
              padding: 4,
              display: "flex",
            }}
            onMouseOver={(e) => (e.currentTarget.style.color = T.ac)}
            onMouseOut={(e) => (e.currentTarget.style.color = T.tx2)}
          >
            <Icon name="logOut" size={16} />
          </button>
        </div>
      )}
    </aside>
  );
}

function SidebarItem({ label, active = false }) {
  return (
    <div
      style={{
        padding: "10px 22px",
        borderLeft: `2px solid ${active ? T.ac : "transparent"}`,
        background: active ? T.acD : "transparent",
        color: active ? T.tx : T.tx2,
        fontWeight: active ? 600 : 400,
        fontFamily: T.fB,
        fontSize: 13,
        transition: "background .12s, color .12s",
        cursor: active ? "default" : "pointer",
      }}
      onMouseOver={(e) => {
        if (!active) e.currentTarget.style.background = "rgba(255,255,255,0.03)";
      }}
      onMouseOut={(e) => {
        if (!active) e.currentTarget.style.background = "transparent";
      }}
    >
      {label}
    </div>
  );
}

function Avatar({ name }) {
  const hue = [...(name ?? "?")].reduce((acc, ch) => acc + ch.charCodeAt(0), 0) % 360;
  const initials = (name ?? "?").slice(0, 2).toUpperCase();
  return (
    <div
      style={{
        width: 30,
        height: 30,
        borderRadius: "50%",
        background: `oklch(0.32 0.1 ${hue})`,
        color: `oklch(0.88 0.08 ${hue})`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: T.fH,
        fontSize: 11,
        fontWeight: 700,
        border: `2px solid ${T.ac}`,
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}

function AuthenticatedHome({ user }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
      <StatCard label="Sesiones activas" value="1" sub="Este navegador" />
      <StatCard label="Intentos fallidos" value="0" sub="Últimos 15 min" />
      <StatCard label="Rol" value="USER" sub="Por defecto" />
      <StatCard label="ID" value={user.id.slice(0, 8)} sub={user.email} />
    </div>
  );
}

function AnonymousHome() {
  return (
    <div
      style={{
        background: T.s2,
        border: `1px solid ${T.bd}`,
        borderRadius: T.r2,
        padding: 28,
        maxWidth: 520,
      }}
    >
      <h2
        style={{
          fontFamily: T.fH,
          fontSize: 21,
          fontWeight: 700,
          letterSpacing: "-0.5px",
          marginBottom: 10,
        }}
      >
        Bienvenido a Competizione
      </h2>
      <p style={{ color: T.tx2, fontSize: 14, lineHeight: 1.5, marginBottom: 18 }}>
        Crea una cuenta o inicia sesión para acceder al panel de análisis y a tus torneos.
      </p>
      <div style={{ display: "flex", gap: 10 }}>
        <Link to="/login" style={{ textDecoration: "none" }}>
          <Btn>Iniciar sesión</Btn>
        </Link>
        <Link to="/register" style={{ textDecoration: "none" }}>
          <Btn variant="ghost">Crear cuenta</Btn>
        </Link>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub }) {
  return (
    <div
      style={{
        background: T.s2,
        border: `1px solid ${T.bd}`,
        borderRadius: T.r2,
        padding: 18,
        transition: "border-color .12s",
      }}
      onMouseOver={(e) => (e.currentTarget.style.borderColor = T.bdM)}
      onMouseOut={(e) => (e.currentTarget.style.borderColor = T.bd)}
    >
      <div
        style={{
          fontFamily: T.fM,
          fontSize: 10,
          color: T.tx3,
          textTransform: "uppercase",
          letterSpacing: 1,
          marginBottom: 10,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: T.fH,
          fontSize: 30,
          fontWeight: 700,
          letterSpacing: "-1px",
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontSize: 11,
            color: T.tx3,
            marginTop: 6,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}
