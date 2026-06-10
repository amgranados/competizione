import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { dashboardApi } from "../api/dashboardApi.js";
import { friendsApi } from "../api/friendsApi.js";
import { useNotifications } from "../context/NotificationContext.jsx";
import Shell from "../components/Shell.jsx";
import Card from "../components/ui/Card.jsx";
import Btn from "../components/ui/Btn.jsx";
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
  const [friendRequests, setFriendRequests] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    const [dashboard, requests] = await Promise.all([
      dashboardApi.getDashboard(),
      friendsApi.getReceivedRequests().catch(() => []),
    ]);
    setData(dashboard);
    setFriendRequests(requests);
  }, []);

  useEffect(() => {
    let active = true;
    load().catch((err) => {
      if (active) setError(err.message || "No se pudo cargar el dashboard");
    });
    return () => {
      active = false;
    };
    // Re-fetch when notifications change (new events may have arrived).
  }, [load, notifications]);

  const acceptFriendRequest = async (requestId) => {
    setError(null);
    try {
      await friendsApi.acceptRequest(requestId);
      await load();
    } catch (err) {
      setError(err.message || "No se pudo aceptar la solicitud");
    }
  };
  const rejectFriendRequest = async (requestId) => {
    setError(null);
    try {
      await friendsApi.rejectRequest(requestId);
      await load();
    } catch (err) {
      setError(err.message || "No se pudo rechazar la solicitud");
    }
  };

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

      {/* Pending friend requests */}
      {friendRequests.length > 0 && (
        <section style={{ marginBottom: 28 }}>
          <SectionHeader title="Solicitudes de amistad" />
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {friendRequests.map((req) => (
              <Card key={req.id} hoverable={false}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 12,
                    flexWrap: "wrap",
                  }}
                >
                  <Link
                    to={`/users/${encodeURIComponent(req.requester_nickname)}`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      textDecoration: "none",
                      color: "inherit",
                      minWidth: 0,
                    }}
                  >
                    <Icon name="user" size={16} color={T.ac} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>
                        {req.requester_nickname}
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
                        quiere ser tu amigo · {new Date(req.created_at).toLocaleString()}
                      </div>
                    </div>
                  </Link>
                  <div style={{ display: "flex", gap: 8 }}>
                    <Btn size="sm" onClick={() => acceptFriendRequest(req.id)}>
                      <Icon name="check" size={12} /> Aceptar
                    </Btn>
                    <Btn size="sm" variant="ghost" onClick={() => rejectFriendRequest(req.id)}>
                      <Icon name="x" size={12} /> Rechazar
                    </Btn>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

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
