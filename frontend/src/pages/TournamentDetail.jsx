import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { tournamentApi } from "../api/tournamentApi.js";
import { useAuth } from "../hooks/useAuth.js";
import { useTournament, useTournamentSchedule } from "../hooks/useTournament.js";
import Shell from "../components/Shell.jsx";
import Card from "../components/ui/Card.jsx";
import Btn from "../components/ui/Btn.jsx";
import Tag from "../components/ui/Tag.jsx";
import Ava from "../components/ui/Ava.jsx";
import Icon from "../components/ui/Icon.jsx";
import StandingsTable from "../components/StandingsTable.jsx";
import TournamentBracket from "../components/TournamentBracket.jsx";
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

export default function TournamentDetail() {
  const { tournamentId } = useParams();
  const { user } = useAuth();
  const { data: tournament, refresh: refreshTournament } = useTournament(tournamentId);
  const { data: schedule, refresh: refreshSchedule } = useTournamentSchedule(tournamentId);
  const [invitations, setInvitations] = useState([]);
  const [invitedUserId, setInvitedUserId] = useState("");
  const [actionError, setActionError] = useState(null);
  const [standings, setStandings] = useState(null);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editFormat, setEditFormat] = useState("round_robin");

  const isOrganizer = user && tournament && tournament.organizer_id === user.id;
  const isTerminal = tournament && (tournament.state === "finished" || tournament.state === "cancelled");
  const canEdit = isOrganizer && (tournament?.state === "draft" || tournament?.state === "open");

  const reloadInvitations = useCallback(async () => {
    if (isOrganizer) {
      const data = await tournamentApi.listInvitations(tournamentId);
      setInvitations(data.filter((inv) => inv.state === "pending"));
    }
  }, [isOrganizer, tournamentId]);

  useEffect(() => {
    reloadInvitations();
  }, [reloadInvitations, tournament?.state]);

  useEffect(() => {
    if (!tournament) return;
    setEditName(tournament.name);
    setEditFormat(tournament.format);
  }, [tournament?.name, tournament?.format]);

  useEffect(() => {
    if (!tournament) return;
    let cancelled = false;
    if (tournament.format === "round_robin" && tournament.state !== "draft") {
      tournamentApi
        .getStandings(tournament.id)
        .then((data) => {
          if (!cancelled) setStandings(data);
        })
        .catch(() => {});
    }
    return () => {
      cancelled = true;
    };
  }, [tournament, schedule]);

  const runAction = async (fn) => {
    setActionError(null);
    try {
      await fn();
      await Promise.all([refreshTournament(), refreshSchedule(), reloadInvitations()]);
    } catch (err) {
      setActionError(err.message || "Acción fallida");
    }
  };

  if (!tournament) {
    return (
      <Shell title="Cargando..." back="/dashboard">
        <p style={{ color: T.tx2 }}>Cargando torneo…</p>
      </Shell>
    );
  }

  const headerActions = isOrganizer && !isTerminal && (
    <>
      {tournament.state === "draft" && (
        <Btn size="sm" onClick={() => runAction(() => tournamentApi.openRegistration(tournamentId))}>
          <Icon name="play" size={12} /> Abrir inscripciones
        </Btn>
      )}
      {tournament.state === "open" && (
        <Btn
          size="sm"
          onClick={() => runAction(() => tournamentApi.start(tournamentId))}
          disabled={(tournament.participants || []).length < 2}
        >
          <Icon name="play" size={12} /> Iniciar
        </Btn>
      )}
      <Btn
        size="sm"
        variant="ghost"
        onClick={() => {
          if (window.confirm("¿Seguro que quieres cancelar el torneo?")) {
            runAction(() => tournamentApi.cancel(tournamentId));
          }
        }}
      >
        <Icon name="x" size={12} /> Cancelar
      </Btn>
    </>
  );

  return (
    <Shell
      title={tournament.name}
      subtitle={`${FORMAT_LABELS[tournament.format]} · ${(tournament.participants || []).length} participantes`}
      back="/dashboard"
      actions={headerActions}
    >
      {/* Status row */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
        <Tag variant={STATE_VARIANTS[tournament.state]}>{STATE_LABELS[tournament.state]}</Tag>
        <span
          style={{
            fontFamily: T.fM,
            fontSize: 10,
            letterSpacing: 1,
            color: T.tx3,
            textTransform: "uppercase",
          }}
        >
          ID {tournament.id.slice(0, 8)}
        </span>
        {actionError && (
          <span role="alert" style={{ color: T.ac, fontSize: 12 }}>
            {actionError}
          </span>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16 }}>
        {/* MAIN COLUMN */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Edit form */}
          {canEdit && (
            <Card hoverable={false}>
              <SectionHeader
                title="Configuración"
                right={
                  <button
                    onClick={() => setEditing((v) => !v)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: T.tx2,
                      cursor: "pointer",
                      fontFamily: T.fB,
                      fontSize: 12,
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    <Icon name="edit" size={12} /> {editing ? "Cerrar" : "Editar"}
                  </button>
                }
              />
              {editing ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const payload = {};
                    if (editName && editName !== tournament.name) payload.name = editName;
                    if (editFormat && editFormat !== tournament.format) payload.format = editFormat;
                    if (Object.keys(payload).length === 0) {
                      setEditing(false);
                      return;
                    }
                    runAction(() => tournamentApi.update(tournamentId, payload)).then(() =>
                      setEditing(false),
                    );
                  }}
                  style={{ display: "flex", gap: 12, alignItems: "end" }}
                >
                  <div style={{ flex: 1 }}>
                    <Field label="Nombre">
                      <input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        maxLength={100}
                        style={inputStyle}
                      />
                    </Field>
                  </div>
                  <div style={{ width: 200 }}>
                    <Field label="Formato">
                      <select
                        value={editFormat}
                        onChange={(e) => setEditFormat(e.target.value)}
                        style={{ ...inputStyle, cursor: "pointer" }}
                      >
                        <option value="round_robin">Round-robin</option>
                        <option value="single_elim">Eliminación directa</option>
                      </select>
                    </Field>
                  </div>
                  <Btn type="submit" size="sm">
                    Guardar
                  </Btn>
                </form>
              ) : (
                <div style={{ color: T.tx2, fontSize: 13 }}>
                  Puedes cambiar nombre y formato mientras el torneo no haya empezado.
                </div>
              )}
            </Card>
          )}

          {/* Schedule / Bracket */}
          {schedule && schedule.rounds?.length > 0 && (
            <Card hoverable={false}>
              <SectionHeader
                title={tournament.format === "single_elim" ? "Cuadro" : "Calendario"}
              />
              {tournament.format === "single_elim" ? (
                <TournamentBracket schedule={schedule} />
              ) : (
                <ScheduleList schedule={schedule} />
              )}
            </Card>
          )}

          {/* Standings */}
          {standings && tournament.format === "round_robin" && (
            <Card hoverable={false}>
              <SectionHeader title="Clasificación" />
              <StandingsTable entries={standings} />
            </Card>
          )}
        </div>

        {/* SIDE COLUMN: participants + invitations */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card hoverable={false}>
            <SectionHeader
              title={`Participantes (${(tournament.participants || []).length})`}
            />
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 0 }}>
              {(tournament.participants || []).map((p, idx, arr) => (
                <li
                  key={p.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "10px 0",
                    borderBottom: idx < arr.length - 1 ? `1px solid ${T.bd}` : "none",
                  }}
                >
                  <Ava name={p.nickname} size={28} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 13,
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {p.nickname}
                    </div>
                    <div
                      style={{
                        fontFamily: T.fM,
                        fontSize: 10,
                        color: T.tx3,
                        letterSpacing: 1,
                      }}
                    >
                      {new Date(p.accepted_at).toLocaleDateString()}
                    </div>
                  </div>
                  {isOrganizer && (tournament.state === "draft" || tournament.state === "open") && (
                    <button
                      onClick={() =>
                        runAction(() => tournamentApi.removeParticipant(tournamentId, p.id))
                      }
                      aria-label={`Eliminar ${p.nickname}`}
                      style={iconButtonStyle}
                      onMouseOver={(e) => (e.currentTarget.style.color = T.ac)}
                      onMouseOut={(e) => (e.currentTarget.style.color = T.tx3)}
                    >
                      <Icon name="trash" size={14} />
                    </button>
                  )}
                </li>
              ))}
              {(tournament.participants || []).length === 0 && (
                <li style={{ color: T.tx3, fontSize: 12, padding: "8px 0" }}>
                  Aún no hay participantes confirmados.
                </li>
              )}
            </ul>
          </Card>

          {/* Invite */}
          {isOrganizer && canEdit && (
            <Card hoverable={false}>
              <SectionHeader title="Invitar" />
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!invitedUserId) return;
                  runAction(async () => {
                    await tournamentApi.invite(tournamentId, invitedUserId);
                    setInvitedUserId("");
                  });
                }}
                style={{ display: "flex", flexDirection: "column", gap: 10 }}
              >
                <Field label="User ID del invitado">
                  <input
                    placeholder="UUID del jugador"
                    value={invitedUserId}
                    onChange={(e) => setInvitedUserId(e.target.value)}
                    style={inputStyle}
                  />
                </Field>
                <Btn type="submit" size="sm">
                  <Icon name="plus" size={12} /> Enviar invitación
                </Btn>
              </form>

              {invitations.length > 0 && (
                <>
                  <div
                    style={{
                      marginTop: 16,
                      paddingTop: 12,
                      borderTop: `1px solid ${T.bd}`,
                      fontFamily: T.fM,
                      fontSize: 10,
                      letterSpacing: 1,
                      color: T.tx3,
                      textTransform: "uppercase",
                    }}
                  >
                    Pendientes ({invitations.length})
                  </div>
                  <ul style={{ listStyle: "none", marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
                    {invitations.map((inv) => (
                      <li
                        key={inv.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          fontSize: 12,
                        }}
                      >
                        <span
                          style={{
                            fontFamily: T.fM,
                            color: T.tx2,
                            flex: 1,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {inv.invited_user_id.slice(0, 8)}
                        </span>
                        <button
                          onClick={() =>
                            runAction(() => tournamentApi.cancelInvitation(tournamentId, inv.id))
                          }
                          aria-label="Cancelar invitación"
                          style={iconButtonStyle}
                          onMouseOver={(e) => (e.currentTarget.style.color = T.ac)}
                          onMouseOut={(e) => (e.currentTarget.style.color = T.tx3)}
                        >
                          <Icon name="x" size={12} />
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </Card>
          )}
        </div>
      </div>
    </Shell>
  );
}

function SectionHeader({ title, right }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 14,
      }}
    >
      <h2
        style={{
          fontFamily: T.fH,
          fontSize: 15,
          fontWeight: 600,
        }}
      >
        {title}
      </h2>
      {right}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label style={{ display: "block" }}>
      <span
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
        {label}
      </span>
      {children}
    </label>
  );
}

const inputStyle = {
  width: "100%",
  background: T.s3,
  border: `1px solid ${T.bd}`,
  borderRadius: T.r,
  padding: "9px 13px",
  color: T.tx,
  fontFamily: T.fB,
  fontSize: 13,
  outline: "none",
};

const iconButtonStyle = {
  background: "transparent",
  border: "none",
  color: T.tx3,
  cursor: "pointer",
  padding: 4,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  transition: "color .12s",
};

function ScheduleList({ schedule }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {schedule.rounds.map((r) => (
        <div key={r.number}>
          <div
            style={{
              fontFamily: T.fM,
              fontSize: 10,
              letterSpacing: 1.2,
              color: T.tx3,
              textTransform: "uppercase",
              marginBottom: 8,
            }}
          >
            Ronda {r.number}
          </div>
          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 0 }}>
            {r.matches.map((m, idx, arr) => (
              <li
                key={m.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "10px 0",
                  borderBottom: idx < arr.length - 1 ? `1px solid ${T.bd}` : "none",
                }}
              >
                {m.is_bye ? (
                  <>
                    <Tag>Bye</Tag>
                    <span style={{ fontFamily: T.fM, color: T.tx2, fontSize: 12 }}>
                      {m.player1_id.slice(0, 8)}
                    </span>
                  </>
                ) : (
                  <Link
                    to={`/matches/${m.id}`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      flex: 1,
                      textDecoration: "none",
                      color: "inherit",
                    }}
                  >
                    <Tag variant={m.state === "manual" ? "green" : "default"}>
                      {m.state === "manual" ? "Resuelto" : "Pendiente"}
                    </Tag>
                    <span style={{ fontFamily: T.fM, color: T.tx2, fontSize: 12, flex: 1 }}>
                      {m.player1_id.slice(0, 8)} vs {m.player2_id?.slice(0, 8)}
                    </span>
                    {m.tournament_code && (
                      <span style={{ fontFamily: T.fM, color: T.tx3, fontSize: 10 }}>
                        {m.tournament_code.slice(0, 8)}
                      </span>
                    )}
                    <Icon name="arrowRight" size={12} color={T.tx3} />
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
