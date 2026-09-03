import ProfileForm from "./ProfileForm.jsx";
import Btn from "./ui/Btn.jsx";
import Icon from "./ui/Icon.jsx";
import { T } from "../styles/theme.js";

export default function EditProfileModal({ profile, onClose, onUpdated }) {
  return (
    <div
      role="dialog"
      aria-label="Editar perfil"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.65)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        zIndex: 50,
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 520,
          maxHeight: "90vh",
          overflowY: "auto",
          background: T.s2,
          border: `1px solid ${T.bd}`,
          borderRadius: T.r2,
          padding: 22,
        }}
      >
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 2,
            background: T.ac,
          }}
        />

        <header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 10,
            marginBottom: 18,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: T.r,
                background: T.acD,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: T.ac,
              }}
            >
              <Icon name="user" size={16} />
            </div>
            <h2
              style={{
                fontFamily: T.fH,
                fontSize: 18,
                fontWeight: 700,
                letterSpacing: "-0.4px",
              }}
            >
              Editar perfil
            </h2>
          </div>
          <Btn variant="ghost" size="sm" onClick={onClose} aria-label="Cerrar">
            <Icon name="x" size={13} />
          </Btn>
        </header>

        <ProfileForm profile={profile} onUpdated={onUpdated} layout="stack" />
      </div>
    </div>
  );
}
