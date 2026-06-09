import { Link } from "react-router-dom";
import Card from "./ui/Card.jsx";
import Icon from "./ui/Icon.jsx";
import { T } from "../styles/theme.js";

// Per-type action phrasing + icon (005-US3, FR-016).
const EVENT_META = {
  MATCH_WIN: { icon: "trophy", action: "ganó una partida en" },
  TOURNAMENT_JOIN: { icon: "users", action: "se unió a" },
  TOURNAMENT_INVITE: { icon: "mail", action: "envió una invitación en" },
  TOURNAMENT_CREATE: { icon: "plus", action: "creó el torneo" },
};

/** Relative "time ago" in Spanish; falls back to an absolute date past a week. */
export function timeAgo(value) {
  const then = new Date(value);
  if (Number.isNaN(then.getTime())) return "";
  const seconds = Math.floor((Date.now() - then.getTime()) / 1000);
  if (seconds < 60) return "ahora";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `hace ${days} d`;
  return then.toLocaleDateString();
}

function ActorLabel({ actor }) {
  const style = { fontWeight: 600, color: T.tx };
  if (actor?.exists && actor?.nickname) {
    return (
      <Link
        to={`/users/${encodeURIComponent(actor.nickname)}`}
        style={{ ...style, textDecoration: "none" }}
      >
        {actor.nickname}
      </Link>
    );
  }
  // Resilient: anonymized/deleted actor → plain text, no link (FR-022).
  return <span style={style}>{actor?.nickname ?? "Alguien"}</span>;
}

function TournamentLabel({ tournament }) {
  if (!tournament) return null;
  const style = { fontWeight: 600, color: T.ac };
  if (tournament.id) {
    return (
      <Link to={`/tournaments/${tournament.id}`} style={{ ...style, textDecoration: "none" }}>
        {tournament.name}
      </Link>
    );
  }
  // Resilient: deleted tournament → plain text, no link (FR-022).
  return <span style={{ ...style, color: T.tx2 }}>{tournament.name}</span>;
}

function ActivityRow({ event }) {
  const meta = EVENT_META[event.event_type] ?? { icon: "bell", action: "" };
  return (
    <Card hoverable={false}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ color: T.ac, display: "flex" }}>
          <Icon name={meta.icon} size={16} />
        </span>
        <div style={{ flex: 1, minWidth: 0, fontSize: 13, color: T.tx2 }}>
          <ActorLabel actor={event.actor} /> {meta.action}{" "}
          <TournamentLabel tournament={event.tournament} />
        </div>
        <span
          style={{
            fontFamily: T.fM,
            fontSize: 10,
            letterSpacing: 1,
            color: T.tx3,
            textTransform: "uppercase",
            whiteSpace: "nowrap",
          }}
        >
          {timeAgo(event.created_at)}
        </span>
      </div>
    </Card>
  );
}

/**
 * Chronological recent-activity feed (005-user-dashboard, US3).
 *
 * Renders up to 6 events newest-first with per-type phrasing, clickable
 * actor/tournament (with no-link fallback when either was deleted), and a
 * client-computed relative time. Shows an informative empty state (FR-021).
 */
export default function ActivityFeed({ events = [] }) {
  if (!events.length) {
    return (
      <Card hoverable={false}>
        <p style={{ color: T.tx2, fontSize: 13, margin: 0 }}>
          Sin actividad reciente todavía.
        </p>
      </Card>
    );
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {events.map((event) => (
        <ActivityRow key={event.id} event={event} />
      ))}
    </div>
  );
}
