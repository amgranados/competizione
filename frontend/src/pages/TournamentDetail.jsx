import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { tournamentApi } from "../api/tournamentApi.js";
import { friendsApi } from "../api/friendsApi.js";
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
  const {
    data: tournament,
    error: tournamentError,
    refresh: refreshTournament,
  } = useTournament(tournamentId);
  const { data: schedule, refresh: refreshSchedule } = useTournamentSchedule(tournamentId);
  const [invitations, setInvitations] = useState([]);
  const [invitedUserId, setInvitedUserId] = useState("");
  const [invitableFriends, setInvitableFriends] = useState([]);
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

  const reloadInvitableFriends = useCallback(async () => {
    if (!isOrganizer || !canEdit) {
      setInvitableFriends([]);
      return;
    }
    try {
      const friends = await friendsApi.getInvitable();
      setInvitableFriends(friends);
    } catch {
      setInvitableFriends([]);
    }
  }, [isOrganizer, canEdit]);

  useEffect(() => {
    reloadInvitableFriends();
  }, [reloadInvitableFriends, invitations]);

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
    if (tournamentError) {
      return (
        <Shell title="Torneo no disponible" back="/dashboard">
          <Card hoverable={false}>
            <p role="alert" style={{ color: T.tx2, fontSize: 13, margin: 0 }}>
              No tienes acceso a este torneo o no existe. Solo los participantes
              e invitados pueden verlo.
            </p>
          </Card>
        </Shell>
      );
    }
    return (
      <Shell title="Cargando..." back="/dashboard">
        <p style={{ color: T.tx2 }}>Cargando torneo…</p>
      </Shell>
    );
  }

  const isParticipant = (tournament.participants || []).some(
    (p) => p.user_id === user?.id,
  );

  // participant.id → nickname, para mostrar nombres en calendario y cuadro.
  const participantNames = Object.fromEntries(
    (tournament.participants || []).map((p) => [p.id, p.nickname]),
  );

  const headerActions = isOrganizer && !isTerminal && (
    <>
      {canEdit && !isParticipant && (
        <Btn
          size="sm"
          variant="ghost"
          onClick={() => runAction(() => tournamentApi.join(tournamentId))}
        >
          <Icon name="users" size={12} /> Participar
        </Btn>
      )}
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
                <TournamentBracket schedule={schedule} names={participantNames} />
              ) : (
                <ScheduleList schedule={schedule} names={participantNames} />
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
              <p
                style={{
                  fontFamily: T.fM,
                  fontSize: 10,
                  letterSpacing: 1,
                  color: T.tx3,
                  textTransform: "uppercase",
                  marginBottom: 10,
                }}
              >
                Solo amigos con cuenta de LoL vinculada
              </p>
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
                <Field label="Amigo">
                  {invitableFriends.length === 0 ? (
                    <p
                      style={{
                        fontSize: 12,
                        color: T.tx3,
                        margin: 0,
                      }}
                    >
                      No tienes amigos con LoL vinculado disponibles para
                      invitar.
                    </p>
                  ) : (
                    <select
                      value={invitedUserId}
                      onChange={(e) => setInvitedUserId(e.target.value)}
                      style={inputStyle}
                    >
                      <option value="">Selecciona un amigo…</option>
                      {invitableFriends.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.nickname}
                        </option>
                      ))}
                    </select>
                  )}
                </Field>
                <Btn type="submit" size="sm" disabled={!invitedUserId}>
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

function playerName(names, participantId) {
  if (!participantId) return "—";
  return names?.[participantId] ?? participantId.slice(0, 8);
}

function MatchPlayer({ name, winner, align = "left" }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        flexDirection: align === "right" ? "row-reverse" : "row",
        minWidth: 0,
        flex: 1,
        justifyContent: align === "right" ? "flex-start" : "flex-end",
      }}
    >
      <span
        style={{
          fontSize: 13,
          fontWeight: winner ? 700 : 500,
          color: winner ? T.tx : T.tx2,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {name}
      </span>
      {winner && <Icon name="trophy" size={12} color={T.ac} />}
      <Ava name={name} size={26} ring={winner} />
    </span>
  );
}

function ScheduleList({ schedule, names }) {
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
          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
            {r.matches.map((m) => (
              <li key={m.id}>
                {m.is_bye ? (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "10px 14px",
                      background: T.s3,
                      border: `1px dashed ${T.bd}`,
                      borderRadius: T.r,
                    }}
                  >
                    <Tag>Bye</Tag>
                    <span style={{ fontSize: 13, color: T.tx2 }}>
                      {playerName(names, m.player1_id)} descansa esta ronda
                    </span>
                  </div>
                ) : (
                  <Link
                    to={`/matches/${m.id}`}
                    aria-label={`Ver partida ${playerName(names, m.player1_id)} contra ${playerName(names, m.player2_id)}`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 14,
                      padding: "12px 14px",
                      background: T.s3,
                      border: `1px solid ${T.bd}`,
                      borderRadius: T.r,
                      textDecoration: "none",
                      color: "inherit",
                      transition: "border-color .12s, background .12s",
                    }}
                    onMouseOver={(e) => {
                      e.currentTarget.style.borderColor = T.ac;
                      e.currentTarget.style.background = T.s4;
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.borderColor = T.bd;
                      e.currentTarget.style.background = T.s3;
                    }}
                  >
                    <Tag variant={m.state === "manual" ? "green" : "default"}>
                      {m.state === "manual" ? "Resuelto" : "Pendiente"}
                    </Tag>
                    <span
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        flex: 1,
                        minWidth: 0,
                      }}
                    >
                      <MatchPlayer
                        name={playerName(names, m.player1_id)}
                        winner={m.winner_participant_id === m.player1_id}
                      />
                      <span
                        style={{
                          fontFamily: T.fH,
                          fontSize: 11,
                          fontWeight: 700,
                          letterSpacing: 1,
                          color: T.ac,
                          flexShrink: 0,
                        }}
                      >
                        VS
                      </span>
                      <MatchPlayer
                        name={playerName(names, m.player2_id)}
                        winner={m.winner_participant_id === m.player2_id}
                        align="right"
                      />
                    </span>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        fontFamily: T.fM,
                        fontSize: 10,
                        letterSpacing: 1,
                        textTransform: "uppercase",
                        color: T.tx3,
                        flexShrink: 0,
                      }}
                    >
                      Ver partida <Icon name="arrowRight" size={12} />
                    </span>
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
