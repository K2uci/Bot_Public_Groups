import Link from "next/link";
import Shell from "@/components/Shell";
import ConfigFields from "@/components/ConfigFields";
import { crearCliente } from "@/app/actions";
import { requireAdmin } from "@/lib/auth";

export default async function Clientes() {
  const { supabase } = await requireAdmin();
  const { data: clientes } = await supabase
    .from("clientes")
    .select("id,slug,nombre,activo,hora_inicio,espera_min,espera_max,cookies_actualizadas")
    .order("nombre");

  return (
    <Shell>
      <h1>Clientes</h1>

      <div className="card">
        <table>
          <thead>
            <tr><th>Cliente</th><th>Estado</th><th>Inicio</th><th>Intervalo</th><th>Cookies</th></tr>
          </thead>
          <tbody>
            {(clientes ?? []).map((c) => (
              <tr key={c.id}>
                <td><Link href={`/clientes/${c.id}`}>{c.nombre}</Link> <span className="suave">({c.slug})</span></td>
                <td>{c.activo ? <span className="ok">activo</span> : <span className="pill">pausado</span>}</td>
                <td>{c.hora_inicio}</td>
                <td>{c.espera_min}–{c.espera_max} min</td>
                <td>{c.cookies_actualizadas ? "✔" : <span className="mal">faltan</span>}</td>
              </tr>
            ))}
            {(clientes ?? []).length === 0 && <tr><td colSpan={5} className="suave">Sin clientes todavía.</td></tr>}
          </tbody>
        </table>
      </div>

      <form action={crearCliente} className="card stack">
        <h2>Nuevo cliente</h2>
        <label>
          Identificador (a-z, 0-9, guion; no se puede cambiar)
          <input name="slug" pattern="[a-z0-9_\-]{2,40}" required />
        </label>
        <ConfigFields />
        <p className="suave">El cliente nace pausado: sube sus cookies, revisa sus grupos y publicaciones, y luego actívalo.</p>
        <button type="submit">Crear cliente</button>
      </form>
    </Shell>
  );
}
