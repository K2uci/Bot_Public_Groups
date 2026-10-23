import Link from "next/link";
import { Activity, AlertTriangle, Bot, CheckCircle2, Clock, Users } from "lucide-react";
import Shell from "@/components/Shell";
import { Badge, CardHead, Empty, PageHead, Stat, type Tono } from "@/components/ui";
import { requireAdmin } from "@/lib/auth";
import { hoyCuba, horaCuba, segundosDesde } from "@/lib/fechas";

type Tanda = {
  cliente_id: string; publicados: number; fallidos: number; pendientes: number; total_grupos: number;
  en_curso: boolean; bloqueo: string | null; inicio: string | null; fin: string | null;
};
type Cliente = { id: string; slug: string; nombre: string; activo: boolean; hora_inicio: string };

function estadoDe(c: Cliente, t?: Tanda): { texto: string; tono: Tono; pulso?: boolean } {
  if (!c.activo) return { texto: "Pausado", tono: "muted" };
  if (t?.bloqueo) return { texto: "Bloqueo", tono: "bad" };
  if (t?.en_curso) return { texto: "Publicando", tono: "ok", pulso: true };
  if (t) return { texto: "Terminado", tono: "primary" };
  return { texto: `Programado ${c.hora_inicio}`, tono: "warn" };
}

export default async function Panel() {
  const { supabase } = await requireAdmin();
  const hoy = hoyCuba();

  const [{ data: bot }, { data: clientes }, { data: tandas }, { count: pendientes }] = await Promise.all([
    supabase.from("bot_estado").select("*").eq("id", 1).maybeSingle(),
    supabase.from("clientes").select("id,slug,nombre,activo,hora_inicio").order("nombre"),
    supabase.from("tandas_dia").select("*").eq("fecha", hoy),
    supabase.from("ordenes").select("id", { count: "exact", head: true }).in("estado", ["pendiente", "en_proceso"]),
  ]);

  const lista = (clientes ?? []) as Cliente[];
  const delDia = (tandas ?? []) as Tanda[];
  const enLinea = segundosDesde(bot?.ultima_conexion) < 180;
  const publicadas = delDia.reduce((n, t) => n + t.publicados, 0);
  const fallidas = delDia.reduce((n, t) => n + t.fallidos, 0);
  const activos = lista.filter((c) => c.activo).length;

  return (
    <Shell>
      <PageHead title="Panel" subtitle={`Resumen de hoy · ${hoy}`} />

      <div className="stats">
        <Stat
          icono={Bot}
          tono={enLinea ? "ok" : "bad"}
          valor={enLinea ? "En línea" : bot ? "Sin señal" : "Sin conectar"}
          etiqueta={bot ? `Último latido ${horaCuba(bot.ultima_conexion)}` : "El bot aún no se ha conectado"}
        />
        <Stat icono={Users} valor={`${activos}/${lista.length}`} etiqueta="Clientes activos" />
        <Stat icono={CheckCircle2} tono="ok" valor={publicadas} etiqueta="Publicadas hoy" />
        <Stat icono={AlertTriangle} tono={fallidas ? "bad" : undefined} valor={fallidas} etiqueta="Fallidas hoy" />
      </div>

      <div className="card">
        <CardHead icono={Activity} titulo="Clientes hoy">
          {(pendientes ?? 0) > 0 && (
            <Badge tono="warn" punto pulso>
              {pendientes} orden(es) en cola
            </Badge>
          )}
        </CardHead>
        {lista.length === 0 ? (
          <Empty icono={Users} titulo="Aún no hay clientes">
            <Link href="/clientes/nuevo">Crea el primero</Link> para empezar a publicar.
          </Empty>
        ) : (
          <div className="grid cols-3">
            {lista.map((c) => {
              const t = delDia.find((x) => x.cliente_id === c.id);
              const e = estadoDe(c, t);
              const total = t?.total_grupos ?? 0;
              const hechos = (t?.publicados ?? 0) + (t?.fallidos ?? 0);
              const pct = total ? Math.min(100, Math.round((hechos / total) * 100)) : 0;
              return (
                <Link key={c.id} href={`/clientes/${c.id}`} className="card client-card" style={{ marginBottom: 0, boxShadow: "none" }}>
                  <div className="row between center">
                    <h3>{c.nombre}</h3>
                    <Badge tono={e.tono} punto={e.tono === "ok"} pulso={e.pulso}>
                      {e.texto}
                    </Badge>
                  </div>
                  <div>
                    <div className="row between small muted" style={{ marginBottom: 6 }}>
                      <span>
                        <span className="ok">{t?.publicados ?? 0} publicadas</span>
                        {t?.fallidos ? <span className="bad"> · {t.fallidos} fallidas</span> : null}
                      </span>
                      <span>{total ? `${hechos}/${total}` : "sin tanda"}</span>
                    </div>
                    <div className={`bar ${t?.fallidos ? "bad" : ""}`}>
                      <span style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                  <div className="meta">
                    <span>
                      <Clock size={14} aria-hidden /> {t?.inicio ? `${t.inicio} → ${t.fin ?? "…"}` : `Inicio ${c.hora_inicio}`}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </Shell>
  );
}
