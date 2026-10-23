import Shell from "@/components/Shell";
import { cambiarPassword } from "@/app/actions";
import { requireAdmin } from "@/lib/auth";
import { usuarioDeCorreo } from "@/lib/usuario";

export default async function Cuenta({ searchParams }: { searchParams: Promise<{ ok?: string; error?: string }> }) {
  const { user } = await requireAdmin();
  const { ok, error } = await searchParams;
  return (
    <Shell>
      <h1>Cuenta</h1>
      <form action={cambiarPassword} className="card stack" style={{ maxWidth: 420 }}>
        <p>Usuario: <strong>{usuarioDeCorreo(user.email)}</strong></p>
        <label>
          Nueva contraseña (mínimo 12 caracteres)
          <input name="nueva" type="password" autoComplete="new-password" minLength={12} required />
        </label>
        <label>
          Repetir contraseña
          <input name="repetir" type="password" autoComplete="new-password" minLength={12} required />
        </label>
        {ok && <p className="ok">Contraseña actualizada.</p>}
        {error === "distintas" && <p className="error">Las contraseñas no coinciden.</p>}
        {error === "corta" && <p className="error">Debe tener al menos 12 caracteres.</p>}
        {error === "fallo" && <p className="error">No se pudo cambiar la contraseña.</p>}
        <button type="submit">Cambiar contraseña</button>
      </form>
    </Shell>
  );
}
