import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import { ApiError } from "../api/authApi.js";
import AuthLayout from "../components/AuthLayout.jsx";
import Btn from "../components/ui/Btn.jsx";
import Input from "../components/ui/Input.jsx";
import Icon from "../components/ui/Icon.jsx";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register({ email, password, nickname: nickname || undefined });
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(typeof err.detail === "string" ? err.detail : "No se pudo crear la cuenta");
      } else {
        setError("No se pudo crear la cuenta");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Crear cuenta"
      subtitle="Tu nickname es opcional: si lo dejas vacío, te asignamos uno."
      footer={
        <>
          ¿Ya tienes cuenta?{" "}
          <Link to="/login">Iniciar sesión</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          icon={<Icon name="mail" />}
        />
        <Input
          label="Contraseña"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          icon={<Icon name="lock" />}
          hint="Mínimo 8 caracteres."
        />
        <Input
          label="Nickname (opcional)"
          type="text"
          autoComplete="username"
          pattern="[A-Za-z]+"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          icon={<Icon name="user" />}
          hint="Sólo letras. Si lo dejas vacío, se genera como user12345."
        />

        {error && (
          <p role="alert" style={{ color: "var(--ac)", fontSize: 13 }}>
            {error}
          </p>
        )}

        <Btn type="submit" disabled={submitting} style={{ width: "100%", marginTop: 6 }}>
          {submitting ? "Creando…" : "Crear cuenta"}
        </Btn>
      </form>
    </AuthLayout>
  );
}
