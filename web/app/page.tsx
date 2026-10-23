import Link from "next/link";
import Shell from "@/components/Shell";
import { requireAdmin } from "@/lib/auth";
import { hoyCuba, horaCuba, segundosDesde } from "@/lib/fechas";

export default async function Panel() {
  const { supabase } = await requireAdmin();
  const hoy = hoyCuba();

  const [{ data: bot }, { data: clientes }, { data: tandas }, { count: pendientes }] = await Promise.all([
    supabase.from("bot_estado").select("*").eq("id", 1).maybeSingle(),
    supabase.from("clientes").select("id,slug,nombre,activo,hora_inicio").order("nombre"),
    supabase.from("tandas_dia").select("*").eq("fecha", hoy),
    supabase.from("ordenes").select("id", { count: "exact", head: true }).in("estado", ["pendiente", "en_proceso"]),
  ]);

  const segundos = segundosDesde(bot?.ultima_conexion);
  const enLinea = segundos < 180;

  return (
    <Shell>
      <h1>Panel</h1>

      <div className="card">
        <h2>Bot del VPS</h2>
        {bot ? (
          <p>
            <span className={enLinea ? "ok" : "mal"}>{enLinea ? "● En línea" : "● Sin señal"}</span>{" "}
            <span className="suave">
              último latido {horaCuba(bot.ultima_conexion)} · {bot.version ?? ""} {bot.mensaje ?? ""}
            </span>
          </p>
        ) : (
          <p className="mal">El bot todavía no se ha conectado a Supabase.</p>
        )}
        <p className="suave">Órdenes pendientes: {pendientes ?? 0}</p>
      </div>

      <div className="card">
        <h2>Hoy ({hoy})</h2>
        <table>
          <thead>
            <tr><th>Cliente</th><th>Estado</th><th>Publicadas</th><th>Fallidas</th><th>Pendientes</th><th>Horario</th></tr>
          </thead>
          <tbody>
            {(clientes ?? []).map((c) => {
              const t = tandas?.find((x) => x.cliente_id === c.id);
              return (
                <tr key={c.id}>
                  <td><Link href={`/clientes/${c.id}`}>{c.nombre}</Link></td>
                  <td>
                    {!c.activo ? <span className="pill">pausado</span>
                      : t?.bloqueo ? <span className="mal">bloqueo</span>
                      : t?.en_curso ? <span className="ok">publicando</span>
                      : t ? "terminado" : `programado ${c.hora_inicio}`}
                  </td>
                  <td className="ok">{t?.publicados ?? 0}</td>
                  <td className={t?.fallidos ? "mal" : ""}>{t?.fallidos ?? 0}</td>
                  <td>{t?.pendientes ?? "-"}</td>
                  <td className="suave">{t?.inicio ? `${t.inicio} → ${t.fin ?? "…"}` : "-"}</td>
                </tr>
              );
            })}
            {(clientes ?? []).length === 0 && (
              <tr><td colSpan={6} className="suave">Aún no hay clientes. <Link href="/clientes">Crear el primero</Link>.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
