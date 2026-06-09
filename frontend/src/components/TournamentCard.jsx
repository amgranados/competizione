import { Link } from "react-router-dom";
import Card from "./ui/Card.jsx";
import Tag from "./ui/Tag.jsx";
import Icon from "./ui/Icon.jsx";
import { T } from "../styles/theme.js";

const STATE_LABELS = {
  in_progress: "En curso",
  open: "Próximo",
};

const STATE_VARIANTS = {
  in_progress: "ac",
  open: "blue",
};

const FORMAT_LABELS = {
  round_robin: "Round-robin",
  single_elim: "Eliminación directa",
};

function formatDate(value) {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString();
}

/**
 * A card in the "Mis torneos" section (005-user-dashboard, US2).
 *
 * Renders the tournament name, state label ("En curso"/"Próximo"), format and
 * players count, plus the current round when in progress or the start date when
 * open (FR-011/FR-012). The whole card links to the tournament detail.
 */
export default function TournamentCard({ tournament }) {
  const {
    id,
    name,
    state,
    format,
    players_count,
    current_round,
    start_at,
  } = tournament;
  const inProgress = state === "in_progress";
  const startLabel = formatDate(start_at);

  return (
    <Link to={`/tournaments/${id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <Card accent={inProgress}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12, gap: 8 }}>
          <Tag variant={STATE_VARIANTS[state] ?? "default"}>{STATE_LABELS[state] ?? state}</Tag>
          <span
            style={{
              fontFamily: T.fM,
              fontSize: 10,
              letterSpacing: 1,
              color: T.tx3,
              textTransform: "uppercase",
            }}
          >
            {FORMAT_LABELS[format] ?? format}
          </span>
        </div>

        <div
          style={{
            fontFamily: T.fH,
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: "-0.4px",
            marginBottom: 8,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {name}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14, color: T.tx3, fontSize: 11 }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <Icon name="users" size={12} />
            {players_count} {players_count === 1 ? "jugador" : "jugadores"}
          </span>
          {inProgress && current_round != null && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Icon name="play" size={12} />
              Ronda {current_round}
            </span>
          )}
          {!inProgress && startLabel && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Icon name="calendar" size={12} />
              {startLabel}
            </span>
          )}
        </div>
      </Card>
    </Link>
  );
}
