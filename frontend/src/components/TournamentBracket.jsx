import { Link } from "react-router-dom";
import { T } from "../styles/theme.js";
import Tag from "./ui/Tag.jsx";

function playerName(names, participantId) {
  if (!participantId) return "—";
  return names?.[participantId] ?? participantId.slice(0, 8);
}

export default function TournamentBracket({ schedule, names }) {
  if (!schedule || !schedule.rounds || schedule.rounds.length === 0) {
    return <p style={{ color: T.tx3, fontSize: 12 }}>Cuadro aún no generado.</p>;
  }
  return (
    <div
      style={{
        display: "flex",
        gap: 24,
        overflowX: "auto",
        paddingBottom: 8,
      }}
    >
      {schedule.rounds.map((round) => (
        <div key={round.number} style={{ minWidth: 220, flexShrink: 0 }}>
          <div
            style={{
              fontFamily: T.fM,
              fontSize: 10,
              letterSpacing: 1.2,
              color: T.tx3,
              textTransform: "uppercase",
              marginBottom: 10,
            }}
          >
            Ronda {round.number}
          </div>
          <ul
            style={{
              listStyle: "none",
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            {round.matches.map((m) => (
              <li key={m.id}>
                {m.is_bye ? (
                  <BracketSlot label={`${playerName(names, m.player1_id)} (bye)`} subtle />
                ) : (
                  <Link to={`/matches/${m.id}`} style={{ textDecoration: "none" }}>
                    <BracketSlot
                      label1={playerName(names, m.player1_id)}
                      label2={playerName(names, m.player2_id)}
                      state={m.state}
                      winnerId={m.winner_participant_id}
                      p1Id={m.player1_id}
                      p2Id={m.player2_id}
                    />
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

function BracketSlot({ label, label1, label2, state, winnerId, p1Id, p2Id, subtle = false }) {
  const isResolved = state === "manual";
  return (
    <div
      style={{
        background: T.s3,
        border: `1px solid ${T.bd}`,
        borderRadius: T.r,
        padding: "10px 12px",
        transition: "border-color .12s, background .12s",
        cursor: subtle ? "default" : "pointer",
      }}
      onMouseOver={(e) => {
        if (!subtle) e.currentTarget.style.borderColor = T.bdM;
      }}
      onMouseOut={(e) => {
        if (!subtle) e.currentTarget.style.borderColor = T.bd;
      }}
    >
      {label ? (
        <div
          style={{
            fontFamily: T.fM,
            fontSize: 12,
            color: T.tx3,
          }}
        >
          {label}
        </div>
      ) : (
        <>
          <PlayerLine label={label1} winner={winnerId === p1Id} />
          <PlayerLine label={label2} winner={winnerId === p2Id} />
          <div style={{ marginTop: 6 }}>
            {isResolved ? (
              <Tag variant="green">Resuelto</Tag>
            ) : (
              <Tag>Pendiente</Tag>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function PlayerLine({ label, winner }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "4px 0",
        fontFamily: T.fM,
        fontSize: 12,
        color: winner ? T.tx : T.tx2,
        fontWeight: winner ? 700 : 400,
      }}
    >
      <span>{label}</span>
      {winner && (
        <span
          style={{
            fontFamily: T.fM,
            fontSize: 9,
            letterSpacing: 1,
            color: T.ac,
            textTransform: "uppercase",
          }}
        >
          ●
        </span>
      )}
    </div>
  );
}
