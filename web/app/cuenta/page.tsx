import type { Metadata } from "next";
import { AlertCircle, CheckCircle2, ShieldCheck } from "lucide-react";
import Shell from "@/components/Shell";
import SubmitButton from "@/components/SubmitButton";
import { CardHead, PageHead } from "@/components/ui";
import { cambiarPassword } from "@/app/actions";
import { requireAdmin } from "@/lib/auth";
import { usuarioDeCorreo } from "@/lib/usuario";

export const metadata: Metadata = { title: "Cuenta" };

export default async function Cuenta({ searchParams }: { searchParams: Promise<{ ok?: string; error?: string }> }) {
  const { user } = await requireAdmin();
  const { ok, error } = await searchParams;
  const errores: Record<string, string> = {
    distintas: "Las contraseñas no coinciden.",
    corta: "Debe tener al menos 12 caracteres.",
    fallo: "No se pudo cambiar la contraseña.",
  };
  return (
    <Shell>
      <PageHead title="Cuenta" subtitle={<>Sesión iniciada como <strong>{usuarioDeCorreo(user.email)}</strong></>} />
      <form action={cambiarPassword} className="card stack" style={{ maxWidth: 460 }}>
        <CardHead icono={ShieldCheck} titulo="Cambiar contraseña" />
        <label>
          Nueva contraseña
          <input name="nueva" type="password" autoComplete="new-password" minLength={12} required />
          <span className="hint">Mínimo 12 caracteres.</span>
        </label>
        <label>
          Repetir contraseña
          <input name="repetir" type="password" autoComplete="new-password" minLength={12} required />
        </label>
        {ok && <p className="msg ok"><CheckCircle2 size={16} aria-hidden /> Contraseña actualizada.</p>}
        {error && errores[error] && <p className="msg error" role="alert"><AlertCircle size={16} aria-hidden /> {errores[error]}</p>}
        <div>
          <SubmitButton pendingText="Guardando…">Cambiar contraseña</SubmitButton>
        </div>
      </form>
    </Shell>
  );
}
