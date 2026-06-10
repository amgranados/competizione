import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { tournamentApi } from "../api/tournamentApi.js";
import { useNotifications } from "../context/NotificationContext.jsx";
import Shell from "../components/Shell.jsx";
import Card from "../components/ui/Card.jsx";
import Btn from "../components/ui/Btn.jsx";
import Input from "../components/ui/Input.jsx";
import Icon from "../components/ui/Icon.jsx";
import TournamentCard from "../components/TournamentCard.jsx";
import UserSearchBar from "../components/UserSearchBar.jsx";
import { T } from "../styles/theme.js";

export default function Tournaments() {
  const { notifications } = useNotifications();
  const [tournaments, setTournaments] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [name, setName] = useState("");
  const [format, setFormat] = useState("round_robin");
  const [startAt, setStartAt] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const refresh = useCallback(async () => {
    try {
      const [t, inv] = await Promise.all([
        tournamentApi.listMine(),
        tournamentApi.listMyInvitations("pending"),
      ]);
      setTournaments(t);
      setInvitations(inv);
    } catch (err) {
      setError(err.message || "No se pudieron cargar los torneos");
    }
  }, []);

  useEffect(() => {
    refresh();
    // Re-fetch when notifications change (new events may have arrived).
  }, [refresh, notifications]);

  const handleCreate = async (event) => {
    event.preventDefault();
    setError(null);
    setCreating(true);
    try {
      const t = await tournamentApi.create({
        name,
        format,
        start_at: startAt ? new Date(startAt).toISOString() : null,
      });
      setName("");
      setStartAt("");
      navigate(`/tournaments/${t.id}`);
    } catch (err) {
      setError(err.message || "No se pudo crear el torneo");
    } finally {
      setCreating(false);
    }
  };

  const acceptInvitation = async (invitationId) => {
    setError(null);
    try {
      await tournamentApi.acceptInvitation(invitationId);
      await refresh();
    } catch (err) {
      setError(err.message || "No se pudo aceptar la invitación");
    }
  };
  const rejectInvitation = async (invitationId) => {
    setError(null);
    try {
      await tournamentApi.rejectInvitation(invitationId);
      await refresh();
    } catch (err) {
      setError(err.message || "No se pudo rechazar la invitación");
    }
  };

  return (
    <Shell title="Torneos" subtitle="CATÁLOGO DE COMPETICIONES" actions={<UserSearchBar />}>
      {error && (
        <Card hoverable={false} style={{ marginBottom: 24 }}>
          <p role="alert" style={{ color: T.ac, fontSize: 13, margin: 0 }}>
            {error}
          </p>
        </Card>
      )}

      {/* Pending invitations */}
      {invitations.length > 0 && (
        <section style={{ marginBottom: 28 }}>
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
                      <div style={{ fontSize: 13, fontWeight: 600 }}>Invitación a torneo</div>
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
      <section style={{ marginBottom: 28 }}>
        <SectionTitle>Crear torneo</SectionTitle>
        <Card hoverable={false}>
          <form
            onSubmit={handleCreate}
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1fr 1fr auto",
              gap: 12,
              alignItems: "end",
            }}
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
            <Input
              label="Fecha de inicio (opcional)"
              type="datetime-local"
              value={startAt}
              onChange={(e) => setStartAt(e.target.value)}
            />
            <Btn type="submit" disabled={creating}>
              <Icon name="plus" size={14} />
              {creating ? "Creando…" : "Crear"}
            </Btn>
          </form>
        </Card>
      </section>

      {/* My tournaments */}
      <section>
        <SectionTitle>Mis torneos</SectionTitle>
        {tournaments.length === 0 ? (
          <Card hoverable={false}>
            <p style={{ color: T.tx2, fontSize: 13, margin: 0 }}>
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
              <TournamentCard
                key={t.id}
                tournament={{
                  ...t,
                  players_count: t.players_count ?? (t.participants?.length ?? 0),
                }}
              />
            ))}
          </div>
        )}
      </section>
    </Shell>
  );
}

function SectionTitle({ children }) {
  return (
    <h2 style={{ fontFamily: T.fH, fontSize: 15, fontWeight: 600, marginBottom: 12 }}>
      {children}
    </h2>
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
          aria-label="Formato"
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
