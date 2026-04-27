import { useContext, useState } from "react";
import { useNavigate } from "react-router-dom";
import { profileApi } from "../api/profileApi.js";
import { AuthContext } from "../context/AuthContext.jsx";
import Btn from "./ui/Btn.jsx";
import Input from "./ui/Input.jsx";
import Icon from "./ui/Icon.jsx";
import { T } from "../styles/theme.js";

export default function DeleteAccountModal({ nickname, onClose }) {
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const auth = useContext(AuthContext);
  const navigate = useNavigate();

  const matches = confirmation === nickname;

  async function onSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await profileApi.deleteAccount(confirmation);
      auth?.setUser?.(null);
      auth?.setStatus?.("anonymous");
      navigate("/login");
    } catch (err) {
      if (err?.status === 409) {
        setError(
          err?.detail ??
            "Tienes torneos activos en curso. Espera a que terminen o abandónalos.",
        );
      } else if (err?.status === 400) {
        setError(err?.detail ?? "La confirmación no coincide con tu nickname.");
      } else {
        setError("No se pudo eliminar la cuenta. Inténtalo de nuevo.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-label="Eliminar cuenta"
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
        if (event.target === event.currentTarget && !submitting) onClose();
      }}
    >
      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 440,
          background: T.s2,
          border: `1px solid ${T.bd}`,
          borderRadius: T.r2,
          padding: 22,
          overflow: "hidden",
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
            gap: 10,
            marginBottom: 14,
          }}
        >
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
            <Icon name="alert" size={16} />
          </div>
          <h2
            style={{
              fontFamily: T.fH,
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: "-0.4px",
            }}
          >
            Eliminar cuenta
          </h2>
        </header>

        <p
          style={{
            fontSize: 13,
            color: T.tx2,
            lineHeight: 1.5,
            marginBottom: 18,
          }}
        >
          Esta acción <strong style={{ color: T.tx }}>elimina tu cuenta de forma permanente</strong>. Para
          confirmar, escribe tu nickname (
          <span
            style={{
              fontFamily: T.fM,
              fontSize: 12,
              color: T.ac,
              letterSpacing: 0.3,
            }}
          >
            {nickname}
          </span>
          ) abajo.
        </p>

        <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Input
            label="Confirmación"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            autoFocus
            placeholder={nickname}
          />
          {error && (
            <p
              role="alert"
              style={{
                fontSize: 12,
                color: T.ac,
              }}
            >
              {error}
            </p>
          )}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={submitting}
            >
              Cancelar
            </Btn>
            <Btn type="submit" disabled={!matches || submitting}>
              <Icon name="trash" size={13} />
              {submitting ? "Eliminando…" : "Confirmar eliminación"}
            </Btn>
          </div>
        </form>
      </div>
    </div>
  );
}
