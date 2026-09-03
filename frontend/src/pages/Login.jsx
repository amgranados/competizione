import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import { ApiError } from "../api/authApi.js";
import AuthLayout from "../components/AuthLayout.jsx";
import Btn from "../components/ui/Btn.jsx";
import Input from "../components/ui/Input.jsx";
import Icon from "../components/ui/Icon.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Credenciales inválidas");
      } else {
        setError("No se pudo iniciar sesión");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Iniciar sesión"
      subtitle="Accede con tu email y contraseña."
      footer={
        <>
          ¿Aún no tienes cuenta?{" "}
          <Link to="/register">Crear una</Link>
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
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          icon={<Icon name="lock" />}
        />

        {error && (
          <p role="alert" style={{ color: "var(--ac)", fontSize: 13 }}>
            {error}
          </p>
        )}

        <Btn type="submit" disabled={submitting} style={{ width: "100%", marginTop: 6 }}>
          {submitting ? "Enviando…" : "Iniciar sesión"}
        </Btn>
      </form>
    </AuthLayout>
  );
}
