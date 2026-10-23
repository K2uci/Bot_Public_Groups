import { login } from "@/app/actions";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return (
    <main className="narrow">
      <h1>Bot Facebook</h1>
      <form action={login} className="card stack">
        <label>
          Usuario
          <input name="usuario" autoComplete="username" autoCapitalize="none" spellCheck={false} required />
        </label>
        <label>
          Contraseña
          <input name="password" type="password" autoComplete="current-password" required />
        </label>
        {error === "credenciales" && <p className="error">Usuario o contraseña incorrectos.</p>}
        {error === "permiso" && <p className="error">Esta cuenta no tiene acceso de administrador.</p>}
        <button type="submit">Entrar</button>
      </form>
    </main>
  );
}
