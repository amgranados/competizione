import { useState } from "react";
import { profileApi } from "../api/profileApi.js";
import Card from "./ui/Card.jsx";
import Btn from "./ui/Btn.jsx";
import Input from "./ui/Input.jsx";
import Icon from "./ui/Icon.jsx";
import { T } from "../styles/theme.js";

export default function ProfileForm({ profile, onUpdated, layout = "grid" }) {
  const containerStyle =
    layout === "stack"
      ? { display: "flex", flexDirection: "column", gap: 12 }
      : {
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: 12,
        };
  return (
    <div style={containerStyle}>
      <NicknameForm profile={profile} onUpdated={onUpdated} />
      <PasswordForm onUpdated={onUpdated} />
      <AvatarForm profile={profile} onUpdated={onUpdated} />
    </div>
  );
}

function FieldStatus({ message, kind }) {
  if (!message) return null;
  const color = kind === "error" ? T.ac : "#4ade80";
  return (
    <p
      role={kind === "error" ? "alert" : "status"}
      data-kind={kind}
      style={{
        fontFamily: T.fM,
        fontSize: 10,
        letterSpacing: 1,
        textTransform: "uppercase",
        color,
        marginTop: 10,
      }}
    >
      {message}
    </p>
  );
}

function FormCard({ title, icon, ariaLabel, children }) {
  return (
    <Card hoverable={false} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <header style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Icon name={icon} size={14} color={T.ac} />
        <h3
          style={{
            fontFamily: T.fH,
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "-0.2px",
          }}
        >
          {title}
        </h3>
      </header>
      <form aria-label={ariaLabel} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {children}
      </form>
    </Card>
  );
}

function NicknameForm({ profile, onUpdated }) {
  const [nickname, setNickname] = useState(profile.nickname);
  const [status, setStatus] = useState({ message: null, kind: null });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setStatus({ message: null, kind: null });
    try {
      await profileApi.updateNickname(nickname);
      setStatus({ message: "Nickname actualizado", kind: "success" });
      await onUpdated?.();
    } catch (err) {
      const detail =
        err?.status === 409
          ? "Nickname no disponible"
          : err?.detail ?? "No se pudo actualizar el nickname";
      setStatus({ message: detail, kind: "error" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <FormCard title="Nickname" icon="user" ariaLabel="Cambiar nickname">
      <Input
        label="Nickname"
        value={nickname}
        onChange={(event) => setNickname(event.target.value)}
        icon={<Icon name="user" />}
      />
      <Btn
        type="submit"
        size="sm"
        disabled={submitting}
        onClick={onSubmit}
        style={{ alignSelf: "flex-start" }}
      >
        {submitting ? "Guardando…" : "Guardar nickname"}
      </Btn>
      <FieldStatus {...status} />
    </FormCard>
  );
}

function PasswordForm({ onUpdated }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [status, setStatus] = useState({ message: null, kind: null });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setStatus({ message: null, kind: null });
    try {
      await profileApi.updatePassword({ current_password: currentPassword, new_password: newPassword });
      setStatus({ message: "Contraseña actualizada", kind: "success" });
      setCurrentPassword("");
      setNewPassword("");
      await onUpdated?.();
    } catch (err) {
      const detail = err?.detail ?? "No se pudo actualizar la contraseña";
      setStatus({ message: detail, kind: "error" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <FormCard title="Contraseña" icon="lock" ariaLabel="Cambiar contraseña">
      <Input
        label="Contraseña actual"
        type="password"
        value={currentPassword}
        onChange={(event) => setCurrentPassword(event.target.value)}
        icon={<Icon name="lock" />}
      />
      <Input
        label="Contraseña nueva"
        type="password"
        value={newPassword}
        onChange={(event) => setNewPassword(event.target.value)}
        icon={<Icon name="key" />}
        hint="Mínimo 8 caracteres"
      />
      <Btn
        type="submit"
        size="sm"
        disabled={submitting}
        onClick={onSubmit}
        style={{ alignSelf: "flex-start" }}
      >
        {submitting ? "Guardando…" : "Guardar contraseña"}
      </Btn>
      <FieldStatus {...status} />
    </FormCard>
  );
}

function AvatarForm({ profile, onUpdated }) {
  const [avatarUrl, setAvatarUrl] = useState(profile.avatar_url ?? "");
  const [status, setStatus] = useState({ message: null, kind: null });
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setStatus({ message: null, kind: null });
    try {
      await profileApi.updateAvatar(avatarUrl.trim() === "" ? null : avatarUrl.trim());
      setStatus({ message: "Avatar actualizado", kind: "success" });
      await onUpdated?.();
    } catch (err) {
      const detail =
        err?.status === 422
          ? "URL no válida"
          : err?.detail ?? "No se pudo actualizar el avatar";
      setStatus({ message: detail, kind: "error" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <FormCard title="Avatar" icon="image" ariaLabel="Cambiar avatar">
      <Input
        label="URL del avatar"
        value={avatarUrl}
        onChange={(event) => setAvatarUrl(event.target.value)}
        placeholder="https://…"
        icon={<Icon name="image" />}
        hint="Deja vacío para volver al avatar por defecto"
      />
      <Btn
        type="submit"
        size="sm"
        disabled={submitting}
        onClick={onSubmit}
        style={{ alignSelf: "flex-start" }}
      >
        {submitting ? "Guardando…" : "Guardar avatar"}
      </Btn>
      <FieldStatus {...status} />
    </FormCard>
  );
}
