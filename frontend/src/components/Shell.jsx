import { Link, useLocation, useNavigate } from "react-router-dom";
import { T } from "../styles/theme.js";
import { useAuth } from "../hooks/useAuth.js";
import Ava from "./ui/Ava.jsx";
import Icon from "./ui/Icon.jsx";
import NotificationsBell from "./NotificationsBell.jsx";

const NAV_ITEMS = [
  { label: "Dashboard", to: "/dashboard", icon: "layout" },
  { label: "Torneos", to: "/tournaments", icon: "trophy" },
  { label: "Amigos", to: "/friends", icon: "users" },
  { label: "Perfil", to: "/profile", icon: "user" },
];

export default function Shell({ title, subtitle, back, actions, children }) {
  const { user, logout } = useAuth();

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
      <Sidebar user={user} onLogout={logout} />

      <section style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <TopBar
          title={title}
          subtitle={subtitle}
          back={back}
          actions={actions}
          user={user}
        />
        <div
          style={{
            padding: "20px 28px 28px",
            overflowY: "auto",
            flex: 1,
          }}
        >
          {children}
        </div>
      </section>
    </div>
  );
}

function Sidebar({ user, onLogout }) {
  const location = useLocation();
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
        <Link to="/dashboard" style={{ textDecoration: "none" }}>
          <div
            style={{
              fontFamily: T.fH,
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "-0.6px",
              color: T.tx,
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
        </Link>
      </div>

      <nav style={{ flex: 1 }}>
        {NAV_ITEMS.map((item, idx) => (
          <NavItem
            key={idx}
            label={item.label}
            to={item.to}
            icon={item.icon}
            active={
              location.pathname === item.to ||
              location.pathname.startsWith(`${item.to}/`)
            }
          />
        ))}
      </nav>

      {user && (
        <div
          style={{
            padding: "14px 22px",
            borderTop: `1px solid ${T.bd}`,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <Ava name={user.nickname} size={30} ring src={user.avatar_url} />
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

function NavItem({ label, to, icon, active }) {
  return (
    <Link
      to={to}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 22px",
        borderLeft: `2px solid ${active ? T.ac : "transparent"}`,
        background: active ? T.acD : "transparent",
        color: active ? T.tx : T.tx2,
        fontWeight: active ? 600 : 400,
        fontFamily: T.fB,
        fontSize: 13,
        textDecoration: "none",
        transition: "background .12s, color .12s",
      }}
      onMouseOver={(e) => {
        if (!active) e.currentTarget.style.background = "rgba(255,255,255,0.03)";
      }}
      onMouseOut={(e) => {
        if (!active) e.currentTarget.style.background = "transparent";
      }}
    >
      <Icon name={icon} size={14} />
      {label}
    </Link>
  );
}

function TopBar({ title, subtitle, back, actions, user }) {
  const navigate = useNavigate();
  return (
    <header
      style={{
        padding: "22px 28px 0",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 16,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
        {back && (
          <button
            onClick={() => navigate(back)}
            aria-label="Volver"
            style={{
              width: 32,
              height: 32,
              borderRadius: T.r,
              background: T.s2,
              border: `1px solid ${T.bd}`,
              color: T.tx2,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "border-color .12s, color .12s",
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.borderColor = T.bdM;
              e.currentTarget.style.color = T.tx;
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.borderColor = T.bd;
              e.currentTarget.style.color = T.tx2;
            }}
          >
            <Icon name="arrowLeft" size={14} />
          </button>
        )}
        <div style={{ minWidth: 0 }}>
          <h1
            style={{
              fontFamily: T.fH,
              fontSize: 24,
              fontWeight: 700,
              letterSpacing: "-0.6px",
              marginBottom: 4,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {title}
          </h1>
          {subtitle && (
            <p
              style={{
                fontFamily: T.fM,
                fontSize: 10,
                letterSpacing: 1.2,
                textTransform: "uppercase",
                color: T.tx3,
              }}
            >
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
        {actions}
        <NotificationsBell />
        {user && <Ava name={user.nickname} size={34} ring src={user.avatar_url} />}
      </div>
    </header>
  );
}
