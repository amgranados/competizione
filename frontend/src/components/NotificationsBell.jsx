import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useNotifications } from "../context/NotificationContext.jsx";
import { notificationApi } from "../api/notificationApi.js";
import Icon from "./ui/Icon.jsx";
import { T } from "../styles/theme.js";

const TYPE_LABELS = {
  invitation_received: "Te han invitado a un torneo",
  invitation_cancelled: "Una invitación ha sido cancelada",
  invitation_accepted: "Han aceptado tu invitación",
  invitation_rejected: "Han rechazado tu invitación",
  tournament_started: "Un torneo ha comenzado",
  tournament_cancelled: "Un torneo ha sido cancelado",
  tournament_finished: "Un torneo ha finalizado",
  match_generated: "Tienes una nueva partida",
  match_resolved: "Se ha resuelto una partida",
  friend_request_received: "Has recibido una solicitud de amistad",
  friend_request_accepted: "Han aceptado tu solicitud de amistad",
};

function targetFor(notification) {
  const { type, tournament_id, match_id } = notification;
  if (type === "friend_request_received" || type === "friend_request_accepted") {
    return "/friends";
  }
  // The pending-invitations panel (accept/reject) lives in the Tournaments page.
  if (type === "invitation_received") return "/tournaments";
  if (match_id) return `/matches/${match_id}`;
  if (tournament_id) return `/tournaments/${tournament_id}`;
  return "/dashboard";
}

export default function NotificationsBell() {
  const { notifications, markRead, refresh } = useNotifications();
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef(null);
  const navigate = useNavigate();

  const items = [...(notifications || [])].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at),
  );
  const unread = items.filter((n) => !n.read_at);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setOpen(false);
    };
    const onKeyDown = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const openNotification = async (notification) => {
    setOpen(false);
    if (!notification.read_at) {
      try {
        await markRead(notification.id);
      } catch {
        // Navigation still makes sense even if marking as read fails.
      }
    }
    navigate(targetFor(notification));
  };

  const markAllRead = async () => {
    try {
      await Promise.all(unread.map((n) => notificationApi.markRead(n.id)));
    } finally {
      await refresh();
    }
  };

  return (
    <div ref={wrapperRef} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Notificaciones"
        aria-expanded={open}
        style={{
          position: "relative",
          width: 34,
          height: 34,
          borderRadius: "50%",
          background: T.s2,
          border: `1px solid ${open ? T.bdM : T.bd}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: open ? T.tx : T.tx2,
          cursor: "pointer",
          transition: "border-color .12s, color .12s",
        }}
        onMouseOver={(e) => {
          e.currentTarget.style.borderColor = T.bdM;
          e.currentTarget.style.color = T.tx;
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.borderColor = open ? T.bdM : T.bd;
          e.currentTarget.style.color = open ? T.tx : T.tx2;
        }}
      >
        <Icon name="bell" size={15} />
        {unread.length > 0 && (
          <span
            aria-label={`${unread.length} notificaciones sin leer`}
            style={{
              position: "absolute",
              top: 6,
              right: 6,
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: T.ac,
              border: `2px solid ${T.s2}`,
            }}
          />
        )}
      </button>

      {open && (
        <div
          role="region"
          aria-label="Panel de notificaciones"
          style={{
            position: "absolute",
            top: 42,
            right: 0,
            width: 340,
            maxHeight: 420,
            overflowY: "auto",
            background: T.s2,
            border: `1px solid ${T.bd}`,
            borderRadius: T.r,
            boxShadow: "0 12px 32px rgba(0,0,0,0.45)",
            zIndex: 50,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 8,
              padding: "12px 14px",
              borderBottom: `1px solid ${T.bd}`,
            }}
          >
            <span style={{ fontFamily: T.fH, fontSize: 13, fontWeight: 600 }}>
              Notificaciones
            </span>
            {unread.length > 0 && (
              <button
                onClick={markAllRead}
                style={{
                  background: "transparent",
                  border: "none",
                  color: T.ac,
                  cursor: "pointer",
                  fontFamily: T.fM,
                  fontSize: 10,
                  letterSpacing: 0.5,
                  padding: 0,
                }}
              >
                Marcar todas como leídas
              </button>
            )}
          </div>

          {items.length === 0 ? (
            <p style={{ padding: "16px 14px", margin: 0, fontSize: 12, color: T.tx2 }}>
              No tienes notificaciones.
            </p>
          ) : (
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {items.slice(0, 15).map((n) => (
                <li key={n.id}>
                  <button
                    onClick={() => openNotification(n)}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 10,
                      width: "100%",
                      textAlign: "left",
                      padding: "11px 14px",
                      background: n.read_at ? "transparent" : T.acD,
                      border: "none",
                      borderBottom: `1px solid ${T.bd}`,
                      color: T.tx,
                      cursor: "pointer",
                    }}
                    onMouseOver={(e) =>
                      (e.currentTarget.style.background = "rgba(255,255,255,0.04)")
                    }
                    onMouseOut={(e) =>
                      (e.currentTarget.style.background = n.read_at ? "transparent" : T.acD)
                    }
                  >
                    <span
                      style={{
                        width: 7,
                        height: 7,
                        borderRadius: "50%",
                        marginTop: 4,
                        flexShrink: 0,
                        background: n.read_at ? T.bd : T.ac,
                      }}
                    />
                    <span style={{ minWidth: 0 }}>
                      <span style={{ display: "block", fontSize: 12, fontWeight: n.read_at ? 400 : 600 }}>
                        {TYPE_LABELS[n.type] ?? n.type}
                      </span>
                      <span
                        style={{
                          display: "block",
                          fontFamily: T.fM,
                          fontSize: 10,
                          letterSpacing: 0.5,
                          color: T.tx3,
                          marginTop: 3,
                        }}
                      >
                        {new Date(n.created_at).toLocaleString()}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
