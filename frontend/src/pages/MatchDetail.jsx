import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { matchApi } from "../api/matchApi.js";
import { tournamentApi } from "../api/tournamentApi.js";
import { useAuth } from "../hooks/useAuth.js";
import Shell from "../components/Shell.jsx";
import Card from "../components/ui/Card.jsx";
import Btn from "../components/ui/Btn.jsx";
import Tag from "../components/ui/Tag.jsx";
import Ava from "../components/ui/Ava.jsx";
import Icon from "../components/ui/Icon.jsx";
import { T } from "../styles/theme.js";

export default function MatchDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [match, setMatch] = useState(null);
  const [tournament, setTournament] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    const m = await matchApi.getById(id);
    setMatch(m);
    const t = await tournamentApi.getById(m.tournament_id);
    setTournament(t);
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (!match || !tournament) {
    return (
      <Shell title="Cargando..." back="/dashboard">
        <p style={{ color: T.tx2 }}>Cargando enfrentamiento…</p>
      </Shell>
    );
  }

  const isOrganizer = user && tournament.organizer_id === user.id;
  const canRegister = isOrganizer && match.state === "pending" && !match.is_bye;

  const player1 = (tournament.participants || []).find((p) => p.id === match.player1_id);
  const player2 = (tournament.participants || []).find((p) => p.id === match.player2_id);
  const winner = (tournament.participants || []).find((p) => p.id === match.winner_participant_id);

  const submitResult = async (winnerParticipantId) => {
    setError(null);
    try {
      const updated = await matchApi.registerManualResult(match.id, winnerParticipantId);
      setMatch(updated);
    } catch (err) {
      setError(err.message || "No se pudo registrar el resultado");
    }
  };

  const copyCode = async () => {
    if (!match.tournament_code) return;
    await navigator.clipboard.writeText(match.tournament_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <Shell
      title="Enfrentamiento"
      subtitle={`Torneo · ${tournament.name.toUpperCase()}`}
      back={`/tournaments/${tournament.id}`}
    >
      {/* Status row */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
        <Tag variant={match.state === "manual" ? "green" : "default"}>
          {match.state === "manual" ? "Introducido manualmente" : "Pendiente"}
        </Tag>
        <span
          style={{
            fontFamily: T.fM,
            fontSize: 10,
            letterSpacing: 1,
            color: T.tx3,
            textTransform: "uppercase",
          }}
        >
          Ronda {match.round_number} · ID {match.id.slice(0, 8)}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16 }}>
        {/* Match faceoff */}
        <Card hoverable={false}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr auto 1fr",
              alignItems: "center",
              gap: 24,
              padding: "8px 0 16px",
            }}
          >
            <PlayerSlot
              participant={player1}
              isWinner={winner?.id === player1?.id}
              align="end"
            />
            <div
              style={{
                fontFamily: T.fH,
                fontSize: 22,
                fontWeight: 700,
                color: T.tx3,
                letterSpacing: "-0.5px",
              }}
            >
              VS
            </div>
            {player2 ? (
              <PlayerSlot
                participant={player2}
                isWinner={winner?.id === player2?.id}
                align="start"
              />
            ) : (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <Tag>Bye — avanza el rival</Tag>
              </div>
            )}
          </div>

          {canRegister && (
            <div
              style={{
                marginTop: 8,
                paddingTop: 16,
                borderTop: `1px solid ${T.bd}`,
              }}
            >
              <div
                style={{
                  fontFamily: T.fM,
                  fontSize: 10,
                  letterSpacing: 1,
                  color: T.tx3,
                  textTransform: "uppercase",
                  marginBottom: 10,
                }}
              >
                Registrar resultado · permanente
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Btn onClick={() => submitResult(match.player1_id)} style={{ flex: 1 }}>
                  Gana {player1?.nickname ?? "jugador 1"}
                </Btn>
                <Btn onClick={() => submitResult(match.player2_id)} style={{ flex: 1 }}>
                  Gana {player2?.nickname ?? "jugador 2"}
                </Btn>
              </div>
              {error && (
                <p role="alert" style={{ color: T.ac, fontSize: 13, marginTop: 10 }}>
                  {error}
                </p>
              )}
            </div>
          )}

          {match.state === "manual" && winner && (
            <div
              style={{
                marginTop: 8,
                paddingTop: 16,
                borderTop: `1px solid ${T.bd}`,
                fontSize: 13,
                color: T.tx2,
              }}
            >
              Ganador:{" "}
              <span style={{ color: T.tx, fontWeight: 600 }}>{winner.nickname}</span>
              {match.resolved_at && (
                <span
                  style={{
                    marginLeft: 8,
                    fontFamily: T.fM,
                    fontSize: 10,
                    letterSpacing: 1,
                    color: T.tx3,
                  }}
                >
                  · {new Date(match.resolved_at).toLocaleString()}
                </span>
              )}
            </div>
          )}
        </Card>

        {/* Side: tournament code */}
        <Card hoverable={false}>
          <h2
            style={{
              fontFamily: T.fH,
              fontSize: 15,
              fontWeight: 600,
              marginBottom: 14,
            }}
          >
            Código de sala
          </h2>
          {match.tournament_code ? (
            <>
              <div
                style={{
                  background: T.s3,
                  border: `1px solid ${T.bd}`,
                  borderRadius: T.r,
                  padding: "10px 13px",
                  fontFamily: T.fM,
                  fontSize: 12,
                  color: T.tx,
                  wordBreak: "break-all",
                  marginBottom: 10,
                }}
              >
                {match.tournament_code}
              </div>
              <Btn size="sm" variant="ghost" onClick={copyCode} style={{ width: "100%" }}>
                <Icon name="copy" size={12} /> {copied ? "Copiado" : "Copiar"}
              </Btn>
              <p
                style={{
                  marginTop: 10,
                  fontFamily: T.fM,
                  fontSize: 10,
                  letterSpacing: 1,
                  color: T.tx3,
                  textTransform: "uppercase",
                }}
              >
                Único para los 2 jugadores y el organizador
              </p>
            </>
          ) : (
            <p style={{ color: T.tx3, fontSize: 12 }}>
              {match.is_bye
                ? "Los byes no generan código de sala."
                : "No tienes permiso para ver este código."}
            </p>
          )}
        </Card>
      </div>
    </Shell>
  );
}

function PlayerSlot({ participant, isWinner, align }) {
  const justify = align === "end" ? "flex-end" : "flex-start";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: justify,
        gap: 12,
        flexDirection: align === "end" ? "row-reverse" : "row",
      }}
    >
      <Ava name={participant?.nickname ?? "?"} size={48} ring={isWinner} />
      <div style={{ textAlign: align === "end" ? "right" : "left" }}>
        <div
          style={{
            fontFamily: T.fH,
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: "-0.4px",
            color: isWinner ? T.tx : T.tx2,
          }}
        >
          {participant?.nickname ?? "—"}
        </div>
        {isWinner && <Tag variant="ac" style={{ marginTop: 4 }}>Ganador</Tag>}
      </div>
    </div>
  );
}
