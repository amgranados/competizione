import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { friendsApi } from "../api/friendsApi.js";
import { useNotifications } from "../context/NotificationContext.jsx";
import Shell from "../components/Shell.jsx";
import Card from "../components/ui/Card.jsx";
import Btn from "../components/ui/Btn.jsx";
import Ava from "../components/ui/Ava.jsx";
import Icon from "../components/ui/Icon.jsx";
import UserSearchBar from "../components/UserSearchBar.jsx";
import { T } from "../styles/theme.js";

export default function Friends() {
  const { notifications } = useNotifications();
  const [friends, setFriends] = useState([]);
  const [requests, setRequests] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    const [friendList, received] = await Promise.all([
      friendsApi.getFriends(),
      friendsApi.getReceivedRequests().catch(() => []),
    ]);
    setFriends(friendList);
    setRequests(received);
  }, []);

  useEffect(() => {
    load().catch((err) => {
      setError(err.message || "No se pudieron cargar los amigos");
    });
    // Re-fetch when notifications change (new events may have arrived).
  }, [load, notifications]);

  const acceptRequest = async (requestId) => {
    setError(null);
    try {
      await friendsApi.acceptRequest(requestId);
      await load();
    } catch (err) {
      setError(err.message || "No se pudo aceptar la solicitud");
    }
  };
  const rejectRequest = async (requestId) => {
    setError(null);
    try {
      await friendsApi.rejectRequest(requestId);
      await load();
    } catch (err) {
      setError(err.message || "No se pudo rechazar la solicitud");
    }
  };
  const removeFriend = async (userId) => {
    setError(null);
    try {
      await friendsApi.removeFriend(userId);
      await load();
    } catch (err) {
      setError(err.message || "No se pudo eliminar al amigo");
    }
  };

  return (
    <Shell title="Amigos" subtitle="TU RED DE JUGADORES" actions={<UserSearchBar />}>
      {error && (
        <Card hoverable={false} style={{ marginBottom: 24 }}>
          <p role="alert" style={{ color: T.ac, fontSize: 13, margin: 0 }}>
            {error}
          </p>
        </Card>
      )}

      {/* Pending received requests */}
      {requests.length > 0 && (
        <section style={{ marginBottom: 28 }}>
          <SectionTitle>Solicitudes recibidas</SectionTitle>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {requests.map((req) => (
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
                    <Ava
                      name={req.requester_nickname}
                      size={30}
                      ring
                      src={req.requester_avatar_url}
                    />
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
                    <Btn size="sm" onClick={() => acceptRequest(req.id)}>
                      <Icon name="check" size={12} /> Aceptar
                    </Btn>
                    <Btn size="sm" variant="ghost" onClick={() => rejectRequest(req.id)}>
                      <Icon name="x" size={12} /> Rechazar
                    </Btn>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Friends list */}
      <section>
        <SectionTitle>
          Mis amigos
          {friends.length > 0 && (
            <span
              style={{
                marginLeft: 8,
                fontFamily: T.fM,
                fontSize: 11,
                color: T.tx3,
                fontWeight: 400,
              }}
            >
              {friends.length}
            </span>
          )}
        </SectionTitle>
        {friends.length === 0 ? (
          <Card hoverable={false}>
            <p style={{ color: T.tx2, fontSize: 13, margin: 0 }}>
              Aún no tienes amigos. Usa el buscador de arriba para encontrar jugadores y
              enviarles una solicitud.
            </p>
          </Card>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
              gap: 12,
            }}
          >
            {friends.map((friend) => (
              <Card key={friend.id} hoverable={false}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 12,
                  }}
                >
                  <Link
                    to={`/users/${encodeURIComponent(friend.nickname)}`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      textDecoration: "none",
                      color: "inherit",
                      minWidth: 0,
                    }}
                  >
                    <Ava name={friend.nickname} size={34} ring src={friend.avatar_url} />
                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {friend.nickname}
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
                        Amigo
                      </div>
                    </div>
                  </Link>
                  <Btn
                    size="sm"
                    variant="ghost"
                    aria-label={`Eliminar a ${friend.nickname}`}
                    onClick={() => removeFriend(friend.id)}
                  >
                    <Icon name="x" size={12} /> Eliminar
                  </Btn>
                </div>
              </Card>
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
