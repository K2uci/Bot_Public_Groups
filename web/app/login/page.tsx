import type { Metadata } from "next";
import { AlertCircle } from "lucide-react";
import { login } from "@/app/actions";
import Logo from "@/components/Logo";
import SubmitButton from "@/components/SubmitButton";

export const metadata: Metadata = { title: "Entrar" };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return (
    <div className="auth">
      <div className="auth-card">
        <div className="logo">
          <Logo size={68} />
        </div>
        <h1>Bot Facebook</h1>
        <p className="sub">Inicia sesión para administrar tus clientes</p>
        <form action={login} className="stack">
          <label>
            Usuario
            <input name="usuario" autoComplete="username" autoCapitalize="none" spellCheck={false} required autoFocus />
          </label>
          <label>
            Contraseña
            <input name="password" type="password" autoComplete="current-password" required />
          </label>
          {error === "credenciales" && (
            <p className="msg error" role="alert">
              <AlertCircle size={16} aria-hidden /> Usuario o contraseña incorrectos.
            </p>
          )}
          {error === "permiso" && (
            <p className="msg error" role="alert">
              <AlertCircle size={16} aria-hidden /> Esta cuenta no tiene acceso de administrador.
            </p>
          )}
          <SubmitButton pendingText="Entrando…">Entrar</SubmitButton>
        </form>
      </div>
    </div>
  );
}
