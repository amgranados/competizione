import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { profileApi } from "../api/profileApi.js";
import { friendsApi } from "../api/friendsApi.js";
import { ApiError } from "../api/authApi.js";
import Shell from "../components/Shell.jsx";
import Card from "../components/ui/Card.jsx";
import Ava from "../components/ui/Ava.jsx";
import Icon from "../components/ui/Icon.jsx";
import LinkedGames from "../components/LinkedGames.jsx";
import FriendshipButton from "../components/FriendshipButton.jsx";
import { T } from "../styles/theme.js";

/**
 * Public profile of another user (004-add-friends, US1).
 *
 * Reuses the LoL composition from /profile (LinkedGames). Never shows
 * edit controls or destructive actions. Mounts FriendshipButton whose
 * state comes from the backend's `relationship_status` (HD-1).
 */
export default function UserProfile() {
  const { nickname } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | loaded | not_found | error
  const [errorMsg, setErrorMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setStatus("loading");
    try {
      const data = await profileApi.getPublicProfile(nickname);
      setProfile(data);
      setStatus("loaded");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setStatus("not_found");
      } else {
        setStatus("error");
      }
    }
  }, [nickname]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handle = async (verb) => {
    if (!profile || busy) return;
    setBusy(true);
    setErrorMsg(null);
    try {
      if (verb === "send") {
        await friendsApi.sendRequest(profile.id);
      } else if (verb === "accept" && profile.pending_request_id) {
        await friendsApi.acceptRequest(profile.pending_request_id);
      } else if (verb === "reject" && profile.pending_request_id) {
        await friendsApi.rejectRequest(profile.pending_request_id);
      } else if (verb === "cancel" && profile.pending_request_id) {
        await friendsApi.cancelRequest(profile.pending_request_id);
      } else if (verb === "remove") {
        await friendsApi.removeFriend(profile.id);
      }
      await refresh();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : null;
      setErrorMsg(typeof detail === "string" ? detail : "Operación fallida.");
    } finally {
      setBusy(false);
    }
  };

  if (status === "loading") {
    return (
      <Shell title="Perfil" subtitle="USUARIO" back="/dashboard">
        <p style={{ color: T.tx2, fontSize: 13 }}>Cargando perfil…</p>
      </Shell>
    );
  }
  if (status === "not_found") {
    return (
      <Shell title="Perfil" subtitle="USUARIO" back="/dashboard">
        <Card hoverable={false}>
          <p role="alert" style={{ color: T.ac, fontSize: 13 }}>
            Usuario no encontrado.
          </p>
        </Card>
      </Shell>
    );
  }
  if (status === "error" || !profile) {
    return (
      <Shell title="Perfil" subtitle="USUARIO" back="/dashboard">
        <Card hoverable={false}>
          <p role="alert" style={{ color: T.ac, fontSize: 13 }}>
            No se pudo cargar el perfil.
          </p>
        </Card>
      </Shell>
    );
  }

  return (
    <Shell
      title="Perfil"
      subtitle={`@${profile.nickname.toUpperCase()}`}
      back="/dashboard"
    >
      <Card hoverable={false} style={{ marginBottom: 28, padding: 22 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 18,
            flexWrap: "wrap",
          }}
        >
          {profile.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt="Avatar"
              style={{
                width: 72,
                height: 72,
                borderRadius: "50%",
                objectFit: "cover",
                border: `2px solid ${T.ac}`,
                flexShrink: 0,
              }}
            />
          ) : (
            <Ava name={profile.nickname} size={72} ring />
          )}
          <div style={{ minWidth: 0, flex: 1 }}>
            <h2
              style={{
                fontFamily: T.fH,
                fontSize: 28,
                fontWeight: 700,
                letterSpacing: "-0.8px",
                marginBottom: 6,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {profile.nickname}
            </h2>
            <div
              style={{
                fontFamily: T.fM,
                fontSize: 10,
                color: T.tx3,
                letterSpacing: 1.2,
                textTransform: "uppercase",
              }}
            >
              JUGADOR
            </div>
          </div>
          <FriendshipButton
            status={profile.relationship_status}
            onSendRequest={() => handle("send")}
            onAccept={() => handle("accept")}
            onReject={() => handle("reject")}
            onCancel={() => handle("cancel")}
            onRemove={() => handle("remove")}
          />
        </div>
        {errorMsg && (
          <p
            role="alert"
            style={{ color: T.ac, fontSize: 12, marginTop: 12 }}
          >
            {errorMsg}
          </p>
        )}
      </Card>

      <section
        style={{
          position: "relative",
          marginBottom: 28,
          padding: "20px 22px",
          background: T.s2,
          border: `1px solid ${T.bd}`,
          borderLeft: `3px solid ${T.ac}`,
          borderRadius: T.r2,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 18,
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: T.r,
              background: T.acD,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: T.ac,
            }}
          >
            <Icon name="gamepad" size={18} />
          </div>
          <div>
            <h2
              style={{
                fontFamily: T.fH,
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: "-0.5px",
                lineHeight: 1.1,
              }}
            >
              Juegos vinculados
            </h2>
            <div
              style={{
                fontFamily: T.fM,
                fontSize: 10,
                color: T.tx3,
                letterSpacing: 1.2,
                textTransform: "uppercase",
                marginTop: 4,
              }}
            >
              Identidad competitiva
            </div>
          </div>
        </div>
        <LinkedGames profile={profile} readOnly />
      </section>
    </Shell>
  );
}
