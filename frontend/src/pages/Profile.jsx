import { useCallback, useEffect, useState } from "react";
import { profileApi } from "../api/profileApi.js";
import Shell from "../components/Shell.jsx";
import Card from "../components/ui/Card.jsx";
import Btn from "../components/ui/Btn.jsx";
import Icon from "../components/ui/Icon.jsx";
import Ava from "../components/ui/Ava.jsx";
import LinkedGames from "../components/LinkedGames.jsx";
import DeleteAccountModal from "../components/DeleteAccountModal.jsx";
import EditProfileModal from "../components/EditProfileModal.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { T } from "../styles/theme.js";

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [status, setStatus] = useState("loading");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const { setUser } = useAuth();

  const refresh = useCallback(async () => {
    try {
      const data = await profileApi.getProfile();
      setProfile(data);
      setStatus("loaded");
      setUser?.((current) =>
        current
          ? { ...current, avatar_url: data.avatar_url, nickname: data.nickname }
          : current,
      );
    } catch {
      setStatus("error");
    }
  }, [setUser]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (status === "loading") {
    return (
      <Shell title="Perfil" subtitle="MI CUENTA">
        <p style={{ color: T.tx2, fontSize: 13 }}>Cargando perfil…</p>
      </Shell>
    );
  }
  if (status === "error" || !profile) {
    return (
      <Shell title="Perfil" subtitle="MI CUENTA">
        <Card hoverable={false}>
          <p role="alert" style={{ color: T.ac, fontSize: 13 }}>
            No se pudo cargar el perfil.
          </p>
        </Card>
      </Shell>
    );
  }

  return (
    <Shell title="Perfil" subtitle={`@${profile.nickname.toUpperCase()}`}>
      <ProfileHeader profile={profile} onEdit={() => setShowEditModal(true)} />

      <GamesSection>
        <LinkedGames profile={profile} onUpdated={refresh} />
      </GamesSection>

      <DangerSection onDelete={() => setShowDeleteModal(true)} />

      {showDeleteModal && (
        <DeleteAccountModal
          nickname={profile.nickname}
          onClose={() => setShowDeleteModal(false)}
        />
      )}
      {showEditModal && (
        <EditProfileModal
          profile={profile}
          onClose={() => setShowEditModal(false)}
          onUpdated={refresh}
        />
      )}
    </Shell>
  );
}

function ProfileHeader({ profile, onEdit }) {
  return (
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
            {profile.email ?? "EMAIL · NO DISPONIBLE"}
          </div>
        </div>
        <Btn variant="ghost" onClick={onEdit}>
          <Icon name="user" size={13} />
          Editar perfil
        </Btn>
      </div>
    </Card>
  );
}

function GamesSection({ children }) {
  return (
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
            Tu identidad competitiva
          </div>
        </div>
      </div>
      {children}
    </section>
  );
}

function DangerSection({ onDelete }) {
  return (
    <section style={{ marginTop: 28 }}>
      <h2
        style={{
          fontFamily: T.fH,
          fontSize: 13,
          fontWeight: 600,
          letterSpacing: 0.3,
          textTransform: "uppercase",
          color: T.tx3,
          marginBottom: 10,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <Icon name="alert" size={12} color={T.ac} />
        Zona peligrosa
      </h2>
      <Card hoverable={false} style={{ borderColor: T.ac }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
              Eliminar cuenta
            </div>
            <p style={{ fontSize: 12, color: T.tx2, lineHeight: 1.5 }}>
              Esta acción es irreversible. Tu cuenta se anonimizará y no podrás
              recuperar el acceso. No se puede ejecutar mientras participes en
              torneos activos.
            </p>
          </div>
          <Btn
            variant="ghost"
            onClick={onDelete}
            style={{ borderColor: T.ac, color: T.ac }}
          >
            <Icon name="trash" size={13} />
            Eliminar cuenta
          </Btn>
        </div>
      </Card>
    </section>
  );
}
