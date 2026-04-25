import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { tournamentApi } from "../api/tournamentApi.js";
import { useAuth } from "../hooks/useAuth.js";
import { useNotifications } from "../context/NotificationContext.jsx";
import Shell from "../components/Shell.jsx";
import Card from "../components/ui/Card.jsx";
import Btn from "../components/ui/Btn.jsx";
import Input from "../components/ui/Input.jsx";
import Tag from "../components/ui/Tag.jsx";
import Icon from "../components/ui/Icon.jsx";
import { T } from "../styles/theme.js";

const STATE_VARIANTS = {
  draft: "default",
  open: "blue",
  active: "ac",
  finished: "green",
  cancelled: "orange",
};

const STATE_LABELS = {
  draft: "Borrador",
  open: "Inscripción",
  active: "En curso",
  finished: "Finalizado",
  cancelled: "Cancelado",
};

const FORMAT_LABELS = {
  round_robin: "Round-robin",
  single_elim: "Eliminación directa",
};

export default function Dashboard() {
  const { user } = useAuth();
  const { notifications } = useNotifications();
  const [tournaments, setTournaments] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [name, setName] = useState("");
  const [format, setFormat] = useState("round_robin");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const refresh = useCallback(async () => {
    const [t, inv] = await Promise.all([
      tournamentApi.listMine(),
      tournamentApi.listMyInvitations("pending"),
    ]);
    setTournaments(t);
    setInvitations(inv);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh, notifications]);

  const stats = useMemo(() => {
    const total = tournaments.length;
    const active = tournaments.filter((t) => t.state === "active").length;
    const drafts = tournaments.filter((t) => t.state === "draft" || t.state === "open").length;
    const finished = tournaments.filter((t) => t.state === "finished").length;
    return { total, active, drafts, finished };
  }, [tournaments]);

  const handleCreate = async (event) => {
    event.preventDefault();
    setError(null);
    setCreating(true);
    try {
      const t = await tournamentApi.create({ name, format });
      setName("");
      navigate(`/tournaments/${t.id}`);
    } catch (err) {
      setError(err.message || "No se pudo crear el torneo");
    } finally {
      setCreating(false);
    }
  };

  const acceptInvitation = async (invitationId) => {
    await tournamentApi.acceptInvitation(invitationId);
    await refresh();
  };
  const rejectInvitation = async (invitationId) => {
    await tournamentApi.rejectInvitation(invitationId);
    await refresh();
  };

  return (
    <Shell title="Dashboard" subtitle={`HOLA, ${user?.nickname?.toUpperCase() ?? ""}`}>
      {/* Stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
          marginBottom: 24,
        }}
      >
        <StatCard label="Torneos totales" value={stats.total} />
        <StatCard label="En curso" value={stats.active} accent />
        <StatCard label="Pre-inicio" value={stats.drafts} />
        <StatCard label="Finalizados" value={stats.finished} />
      </div>

      {/* Pending invitations */}
      {invitations.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <SectionTitle>Invitaciones pendientes</SectionTitle>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {invitations.map((inv) => (
              <Card key={inv.id} hoverable={false}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 12,
                    flexWrap: "wrap",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
                    <Icon name="mail" size={16} color={T.ac} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>
                        Torneo
                      </div>
                      <div
                        style={{
                          fontFamily: T.fM,
                          fontSize: 10,
                          letterSpacing: 1,
                          color: T.tx3,
                          textTransform: "uppercase",
                        }}
                      >
                        {inv.tournament_id.slice(0, 8)} · expira{" "}
                        {new Date(inv.expires_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <Btn size="sm" onClick={() => acceptInvitation(inv.id)}>
                      <Icon name="check" size={12} /> Aceptar
                    </Btn>
                    <Btn size="sm" variant="ghost" onClick={() => rejectInvitation(inv.id)}>
                      <Icon name="x" size={12} /> Rechazar
                    </Btn>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Create tournament */}
      <section style={{ marginBottom: 24 }}>
        <SectionTitle>Crear torneo</SectionTitle>
        <Card hoverable={false}>
          <form
            onSubmit={handleCreate}
            style={{ display: "grid", gridTemplateColumns: "2fr 1fr auto", gap: 12, alignItems: "end" }}
          >
            <Input
              label="Nombre"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={1}
              maxLength={100}
              icon={<Icon name="trophy" />}
            />
            <FormatSelect value={format} onChange={setFormat} />
            <Btn type="submit" disabled={creating}>
              <Icon name="plus" size={14} />
              {creating ? "Creando…" : "Crear"}
            </Btn>
          </form>
          {error && (
            <p role="alert" style={{ color: T.ac, fontSize: 13, marginTop: 12 }}>
              {error}
            </p>
          )}
        </Card>
      </section>

      {/* My tournaments */}
      <section>
        <SectionTitle>Mis torneos</SectionTitle>
        {tournaments.length === 0 ? (
          <Card hoverable={false}>
            <p style={{ color: T.tx2, fontSize: 13 }}>
              No tienes torneos todavía. Crea uno arriba para empezar.
            </p>
          </Card>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 12,
            }}
          >
            {tournaments.map((t) => (
              <Link
                key={t.id}
                to={`/tournaments/${t.id}`}
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <Card accent={t.state === "active"}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                    <Tag variant={STATE_VARIANTS[t.state]}>{STATE_LABELS[t.state]}</Tag>
                    <span
                      style={{
                        fontFamily: T.fM,
                        fontSize: 10,
                        letterSpacing: 1,
                        color: T.tx3,
                        textTransform: "uppercase",
                      }}
                    >
                      {FORMAT_LABELS[t.format]}
                    </span>
                  </div>
                  <div
                    style={{
                      fontFamily: T.fH,
                      fontSize: 18,
                      fontWeight: 700,
                      letterSpacing: "-0.4px",
                      marginBottom: 6,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {t.name}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, color: T.tx3, fontSize: 11 }}>
                    <Icon name="users" size={12} />
                    <span>{(t.participants || []).length} participantes</span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>
    </Shell>
  );
}

function SectionTitle({ children }) {
  return (
    <h2
      style={{
        fontFamily: T.fH,
        fontSize: 15,
        fontWeight: 600,
        marginBottom: 12,
      }}
    >
      {children}
    </h2>
  );
}

function StatCard({ label, value, accent = false }) {
  return (
    <Card accent={accent}>
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
    </Card>
  );
}

function FormatSelect({ value, onChange }) {
  return (
    <div>
      <label
        style={{
          display: "block",
          fontFamily: T.fB,
          fontSize: 12,
          fontWeight: 500,
          color: T.tx2,
          letterSpacing: 0.3,
          marginBottom: 6,
        }}
      >
        Formato
      </label>
      <div
        style={{
          background: T.s3,
          border: `1px solid ${T.bd}`,
          borderRadius: T.r,
          padding: "10px 13px",
          display: "flex",
          alignItems: "center",
        }}
      >
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={{
            flex: 1,
            background: "transparent",
            color: T.tx,
            border: "none",
            outline: "none",
            fontFamily: T.fB,
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          <option value="round_robin">Round-robin</option>
          <option value="single_elim">Eliminación directa</option>
        </select>
      </div>
    </div>
  );
}
