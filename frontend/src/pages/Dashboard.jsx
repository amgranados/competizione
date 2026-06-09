import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { dashboardApi } from "../api/dashboardApi.js";
import { useNotifications } from "../context/NotificationContext.jsx";
import Shell from "../components/Shell.jsx";
import Card from "../components/ui/Card.jsx";
import StatsCard from "../components/StatsCard.jsx";
import TournamentCard from "../components/TournamentCard.jsx";
import ActivityFeed from "../components/ActivityFeed.jsx";
import UserSearchBar from "../components/UserSearchBar.jsx";
import Icon from "../components/ui/Icon.jsx";
import { T } from "../styles/theme.js";

function formatWinrate(winrate, gamesPlayed) {
  if (winrate == null || !gamesPlayed) return "0%";
  return `${Math.round(winrate)}%`;
}

export default function Dashboard() {
  const { notifications } = useNotifications();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    dashboardApi
      .getDashboard()
      .then((d) => {
        if (active) setData(d);
      })
      .catch((err) => {
        if (active) setError(err.message || "No se pudo cargar el dashboard");
      });
    return () => {
      active = false;
    };
    // Re-fetch when notifications change (new events may have arrived).
  }, [notifications]);

  const stats = data?.stats;

  return (
    <Shell title="Dashboard" subtitle={data?.subtitle ?? ""} actions={<UserSearchBar />}>
      {error && (
        <Card hoverable={false} style={{ marginBottom: 24 }}>
          <p role="alert" style={{ color: T.ac, fontSize: 13, margin: 0 }}>
            {error}
          </p>
        </Card>
      )}

      {/* Greeting */}
      <h2
        style={{
          fontFamily: T.fH,
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: "-0.5px",
          marginBottom: 20,
        }}
      >
        {data?.greeting ?? ""}
      </h2>

      {/* Stat cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
          marginBottom: 28,
        }}
      >
        <StatsCard
          label="Torneos activos"
          value={stats?.active_tournaments.count ?? 0}
          delta={stats?.active_tournaments.weekly_delta ?? null}
          accent
        />
        <StatsCard
          label="Victorias"
          value={stats?.total_wins.wins ?? 0}
          subvalue={formatWinrate(stats?.total_wins.winrate, stats?.total_wins.games_played)}
        />
        <StatsCard
          label="Mejor streak"
          value={stats?.best_streak.best ?? 0}
          subvalue={stats?.best_streak.tournament_name ?? null}
        />
        <StatsCard label="Amigos" value={stats?.friends_count ?? 0} />
      </div>

      {/* My tournaments */}
      <section style={{ marginBottom: 28 }}>
        <SectionHeader title="Mis torneos">
          <Link
            to="/tournaments"
            style={{
              fontFamily: T.fM,
              fontSize: 11,
              letterSpacing: 0.5,
              color: T.ac,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            Ver todos <Icon name="arrowRight" size={12} />
          </Link>
        </SectionHeader>
        {data && data.my_tournaments.length === 0 ? (
          <Card hoverable={false}>
            <p style={{ color: T.tx2, fontSize: 13, margin: 0 }}>
              No tienes torneos activos ni próximos. ¡Únete o crea uno desde Torneos!
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
            {(data?.my_tournaments ?? []).map((t) => (
              <TournamentCard key={t.id} tournament={t} />
            ))}
          </div>
        )}
      </section>

      {/* Activity feed */}
      <section>
        <SectionHeader title="Actividad reciente" />
        <ActivityFeed events={data?.activity ?? []} />
      </section>
    </Shell>
  );
}

function SectionHeader({ title, children }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: 12,
      }}
    >
      <h2 style={{ fontFamily: T.fH, fontSize: 15, fontWeight: 600, margin: 0 }}>{title}</h2>
      {children}
    </div>
  );
}
