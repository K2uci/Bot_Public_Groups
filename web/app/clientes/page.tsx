import type { Metadata } from "next";
import Link from "next/link";
import { CalendarDays, Clock, KeyRound, Plus, Timer, Users } from "lucide-react";
import Shell from "@/components/Shell";
import { Badge, Empty, PageHead } from "@/components/ui";
import { requireAdmin } from "@/lib/auth";
import { DIAS } from "@/lib/fechas";

export const metadata: Metadata = { title: "Clientes" };

export default async function Clientes() {
  const { supabase } = await requireAdmin();
  const { data: clientes } = await supabase
    .from("clientes")
    .select("id,slug,nombre,activo,hora_inicio,espera_min,espera_max,dias_semana,cookies_actualizadas")
    .order("nombre");
  const lista = clientes ?? [];

  return (
    <Shell>
      <PageHead title="Clientes" subtitle={`${lista.length} cliente(s) registrado(s)`}>
        <Link href="/clientes/nuevo" className="btn primary">
          <Plus size={16} aria-hidden /> Nuevo cliente
        </Link>
      </PageHead>

      {lista.length === 0 ? (
        <div className="card">
          <Empty icono={Users} titulo="Todavía no hay clientes">
            Crea el primero, sube sus cookies y actívalo.
          </Empty>
        </div>
      ) : (
        <div className="grid cols-3">
          {lista.map((c) => (
            <Link key={c.id} href={`/clientes/${c.id}`} className="card client-card" style={{ marginBottom: 0 }}>
              <div className="row between center">
                <div>
                  <h3>{c.nombre}</h3>
                  <span className="muted small">{c.slug}</span>
                </div>
                {c.activo ? <Badge tono="ok" punto>Activo</Badge> : <Badge>Pausado</Badge>}
              </div>
              <div className="meta">
                <span><Clock size={14} aria-hidden /> {c.hora_inicio}</span>
                <span><Timer size={14} aria-hidden /> {c.espera_min}–{c.espera_max} min</span>
                <span>
                  <CalendarDays size={14} aria-hidden />{" "}
                  {c.dias_semana ? (c.dias_semana as number[]).map((d) => DIAS[d]).join(" ") : "Todos los días"}
                </span>
              </div>
              <div>
                {c.cookies_actualizadas ? (
                  <Badge tono="ok"><KeyRound size={12} aria-hidden /> Cookies cifradas</Badge>
                ) : (
                  <Badge tono="bad"><KeyRound size={12} aria-hidden /> Faltan cookies</Badge>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </Shell>
  );
}
