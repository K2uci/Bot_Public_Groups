import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  AlertTriangle, ArrowLeft, CheckCircle2, Clock, ExternalLink, Eye, EyeOff, History, Image as ImageIcon, KeyRound,
  Layers, ListChecks, Pause, Play, RefreshCw, Send, Settings, Trash2, Users, Zap,
} from "lucide-react";
import Shell from "@/components/Shell";
import ConfigFields from "@/components/ConfigFields";
import CookiesUpload from "@/components/CookiesUpload";
import ImagenInput from "@/components/ImagenInput";
import SubmitButton from "@/components/SubmitButton";
import { Badge, CardHead, Empty, PageHead, Stat, type Tono } from "@/components/ui";
import { requireAdmin } from "@/lib/auth";
import { DIAS, hoyCuba, horaCuba } from "@/lib/fechas";
import {
  activarCliente, activarGrupo, activarPublicacion, agregarGrupo, crearOrden, crearPublicacion,
  editarPublicacion, eliminarCliente, eliminarPublicacion, guardarCliente,
} from "@/app/actions";

export const metadata: Metadata = { title: "Cliente" };

const TABS = [
  { key: "resumen", label: "Resumen", icon: Layers },
  { key: "publicaciones", label: "Publicaciones", icon: ImageIcon },
  { key: "grupos", label: "Grupos", icon: Users },
  { key: "configuracion", label: "Configuración", icon: Settings },
  { key: "historial", label: "Historial", icon: History },
] as const;
type TabKey = (typeof TABS)[number]["key"];

// Algunos grupos se detectan sin nombre (solo su numero): se muestran como "Grupo <id>"
function etiquetaGrupo(g: { nombre: string | null; url: string }): string {
  return g.nombre && !/^\d+$/.test(g.nombre) ? g.nombre : `Grupo ${g.url.split("/").pop()}`;
}

const TONO_ORDEN: Record<string, Tono> = { pendiente: "warn", en_proceso: "primary", hecha: "ok", error: "bad" };

export default async function ClienteDetalle({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const { id } = await params;
  const { tab: tabParam } = await searchParams;
  const tab: TabKey = TABS.some((t) => t.key === tabParam) ? (tabParam as TabKey) : "resumen";
  const { supabase } = await requireAdmin();

  const { data: c } = await supabase.from("clientes").select("*").eq("id", id).maybeSingle();
  if (!c) notFound();

  const [{ data: grupos }, { data: pubs }, { data: tandas }, { data: log }, { data: ordenes }] = await Promise.all([
    supabase.from("grupos").select("*").eq("cliente_id", id).order("nombre"),
    supabase.from("publicaciones").select("*").eq("cliente_id", id).order("creada"),
    supabase.from("tandas_dia").select("*").eq("cliente_id", id).order("fecha", { ascending: false }).limit(14),
    supabase.from("publicaciones_log").select("*").eq("cliente_id", id).order("creado", { ascending: false }).limit(100),
    supabase.from("ordenes").select("*").eq("cliente_id", id).order("creada", { ascending: false }).limit(8),
  ]);

  // Las imagenes viven en un bucket privado: se muestran con URLs firmadas temporales
  const firmadas = pubs?.length
    ? (await supabase.storage.from("imagenes").createSignedUrls(pubs.map((p) => p.imagen_path), 3600)).data ?? []
    : [];
  const urlDe = (path: string) => firmadas.find((f) => f.path === path)?.signedUrl;

  const gruposActivos = (grupos ?? []).filter((g) => g.activo).length;
  const pubsActivas = (pubs ?? []).filter((p) => p.activo).length;
  const hoy = (tandas ?? []).find((t) => t.fecha === hoyCuba());
  const href = (t: TabKey) => `/clientes/${id}?tab=${t}`;
  const conteo: Partial<Record<TabKey, number>> = { publicaciones: pubsActivas, grupos: gruposActivos };

  return (
    <Shell>
      <Link href="/clientes" className="muted small row center" style={{ gap: 4, marginBottom: 10 }}>
        <ArrowLeft size={14} aria-hidden /> Clientes
      </Link>
      <PageHead
        title={c.nombre}
        subtitle={
          <>
            {c.slug} · inicio {c.hora_inicio} · cada {c.espera_min}–{c.espera_max} min ·{" "}
            {c.dias_semana ? (c.dias_semana as number[]).map((d) => DIAS[d]).join(" ") : "todos los días"}
          </>
        }
      >
        {c.activo ? <Badge tono="ok" punto pulso>Activo</Badge> : <Badge>Pausado</Badge>}
        <form action={activarCliente.bind(null, id, !c.activo)}>
          <SubmitButton className={c.activo ? "btn" : "btn primary"}>
            {c.activo ? <><Pause size={16} aria-hidden /> Pausar</> : <><Play size={16} aria-hidden /> Activar cliente</>}
          </SubmitButton>
        </form>
      </PageHead>

      <nav className="tabs" aria-label="Secciones del cliente">
        {TABS.map(({ key, label, icon: Icon }) => (
          <Link key={key} href={href(key)} aria-current={tab === key ? "page" : undefined}>
            <Icon size={16} aria-hidden /> {label}
            {conteo[key] !== undefined && <span className="count">{conteo[key]}</span>}
          </Link>
        ))}
      </nav>

      {/* ============================================================ RESUMEN */}
      {tab === "resumen" && (
        <>
          {!c.activo && (
            <p className="msg" style={{ background: "var(--warn-soft)", color: "var(--warn)", marginBottom: "1.1rem" }}>
              <Pause size={16} aria-hidden /> Cliente pausado: el bot no publicará hasta que lo actives.
            </p>
          )}
          <div className="stats">
            <Stat icono={CheckCircle2} tono="ok" valor={hoy?.publicados ?? 0} etiqueta="Publicadas hoy" />
            <Stat icono={AlertTriangle} tono={hoy?.fallidos ? "bad" : undefined} valor={hoy?.fallidos ?? 0} etiqueta="Fallidas hoy" />
            <Stat icono={ListChecks} valor={hoy?.pendientes ?? gruposActivos} etiqueta="Grupos pendientes" />
            <Stat icono={Clock} valor={hoy?.inicio ? `${hoy.inicio} → ${hoy.fin ?? "…"}` : "—"} etiqueta="Horario de hoy" />
          </div>
          {hoy?.bloqueo && (
            <p className="msg error" style={{ marginBottom: "1.1rem" }}>
              <AlertTriangle size={16} aria-hidden /> Bloqueo detectado: {hoy.bloqueo}
            </p>
          )}

          <div className="card">
            <CardHead icono={Zap} titulo="Acciones">
              <span className="hint">Las ejecuta el bot en menos de un minuto.</span>
            </CardHead>
            <div className="row">
              <form action={crearOrden.bind(null, id, "publicar_ahora")} className="row">
                <label style={{ width: 170 }}>
                  Máx. grupos
                  <input name="limite" type="number" min="1" placeholder="Todos los pendientes" />
                </label>
                <SubmitButton pendingText="Enviando…"><Send size={16} aria-hidden /> Publicar ahora</SubmitButton>
              </form>
              <form action={crearOrden.bind(null, id, "leer_grupos")}>
                <SubmitButton className="btn" pendingText="Enviando…"><RefreshCw size={16} aria-hidden /> Releer grupos</SubmitButton>
              </form>
              <form action={crearOrden.bind(null, id, "enviar_resumen")}>
                <SubmitButton className="btn" pendingText="Enviando…"><Send size={16} aria-hidden /> Resumen a Telegram</SubmitButton>
              </form>
            </div>
            {(ordenes ?? []).length > 0 && (
              <div className="table-wrap" style={{ marginTop: "1rem" }}>
                <table>
                  <thead><tr><th>Orden</th><th>Estado</th><th>Creada</th><th>Resultado</th></tr></thead>
                  <tbody>
                    {ordenes!.map((o) => (
                      <tr key={o.id}>
                        <td>{o.tipo.replace("_", " ")}</td>
                        <td><Badge tono={TONO_ORDEN[o.estado] ?? "muted"}>{o.estado.replace("_", " ")}</Badge></td>
                        <td className="muted nowrap">{horaCuba(o.creada)}</td>
                        <td className="muted">{o.resultado ?? ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card stack">
            <CardHead icono={KeyRound} titulo="Cookies de Facebook">
              {c.cookies_actualizadas ? <Badge tono="ok">Cifradas · {horaCuba(c.cookies_actualizadas)}</Badge> : <Badge tono="bad">Sin cookies</Badge>}
            </CardHead>
            {!c.cookies_actualizadas && (
              <p className="msg error"><AlertTriangle size={16} aria-hidden /> Sin cookies el bot no puede entrar a la cuenta de este cliente.</p>
            )}
            <p className="muted small">
              Se generan en tu PC con <code>python login_manual.py {c.slug}</code>: el cliente inicia sesión en la ventana de Edge.
            </p>
            <CookiesUpload clienteId={id} />
          </div>
        </>
      )}

      {/* ============================================================ PUBLICACIONES */}
      {tab === "publicaciones" && (
        <>
          <form action={crearPublicacion.bind(null, id)} className="card stack">
            <CardHead icono={ImageIcon} titulo="Nueva publicación">
              <span className="hint">Rotan una tras otra entre los grupos.</span>
            </CardHead>
            <label>
              Texto
              <textarea name="texto" placeholder="Escribe el texto de la publicación…" required />
            </label>
            <label>
              Imagen
              <ImagenInput />
              <span className="hint">JPG, PNG o WEBP, máximo 4 MB.</span>
            </label>
            <div><SubmitButton pendingText="Subiendo…">Añadir publicación</SubmitButton></div>
          </form>

          {(pubs ?? []).length === 0 ? (
            <div className="card"><Empty icono={ImageIcon} titulo="Sin publicaciones">Añade al menos una (texto + imagen) para que el bot pueda publicar.</Empty></div>
          ) : (
            <div className="grid cols-3">
              {pubs!.map((p) => (
                <div key={p.id} className={`card pub-card ${p.activo ? "" : "off"}`}>
                  {urlDe(p.imagen_path) ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={urlDe(p.imagen_path) ?? undefined} alt="" loading="lazy" />
                  ) : (
                    <div className="noimg"><ImageIcon size={32} aria-hidden /></div>
                  )}
                  <div className="pub-body">
                    <div className="row between center">
                      {p.activo ? <Badge tono="ok" punto>Activa</Badge> : <Badge>Pausada</Badge>}
                      <span className="muted small">{horaCuba(p.creada)}</span>
                    </div>
                    <form action={editarPublicacion.bind(null, id, p.id)} className="stack" style={{ gap: 8 }}>
                      <textarea name="texto" defaultValue={p.texto} required style={{ minHeight: 130, fontSize: "0.88rem" }} />
                      <div><SubmitButton className="btn sm" pendingText="Guardando…">Guardar texto</SubmitButton></div>
                    </form>
                    <div className="row center" style={{ gap: 6 }}>
                      <form action={activarPublicacion.bind(null, id, p.id, !p.activo)}>
                        <SubmitButton className="btn sm ghost">
                          {p.activo ? <><EyeOff size={14} aria-hidden /> Pausar</> : <><Eye size={14} aria-hidden /> Activar</>}
                        </SubmitButton>
                      </form>
                      <form action={eliminarPublicacion.bind(null, id, p.id)}>
                        <SubmitButton className="btn sm ghost danger" confirmar="¿Eliminar esta publicación y su imagen?">
                          <Trash2 size={14} aria-hidden /> Eliminar
                        </SubmitButton>
                      </form>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ============================================================ GRUPOS */}
      {tab === "grupos" && (
        <div className="card stack">
          <CardHead icono={Users} titulo={`Grupos (${gruposActivos} activos de ${grupos?.length ?? 0})`}>
            <span className="hint">El bot revisa la cuenta cada día y añade aquí los grupos nuevos.</span>
          </CardHead>
          <form action={agregarGrupo.bind(null, id)} className="row">
            <label style={{ flex: "2 1 260px" }}>
              URL del grupo
              <input name="url" placeholder="https://www.facebook.com/groups/…" required />
            </label>
            <label style={{ flex: "1 1 180px" }}>
              Nombre (opcional)
              <input name="nombre" />
            </label>
            <SubmitButton className="btn" pendingText="Añadiendo…">Añadir</SubmitButton>
          </form>
          {(grupos ?? []).length === 0 ? (
            <Empty icono={Users} titulo="Sin grupos">Pulsa «Releer grupos» en Resumen o añade uno a mano.</Empty>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Grupo</th><th>Detectado</th><th>Estado</th><th></th></tr></thead>
                <tbody>
                  {grupos!.map((g) => (
                    <tr key={g.id}>
                      <td style={{ opacity: g.activo ? 1 : 0.55 }}>
                        <a href={g.url} target="_blank" rel="noreferrer" className="row center" style={{ gap: 6 }}>
                          {etiquetaGrupo(g)} <ExternalLink size={13} aria-hidden />
                        </a>
                      </td>
                      <td className="muted nowrap">{horaCuba(g.detectado)}</td>
                      <td>{g.activo ? <Badge tono="ok">Activo</Badge> : <Badge>Excluido</Badge>}</td>
                      <td style={{ textAlign: "right" }}>
                        <form action={activarGrupo.bind(null, id, g.id, !g.activo)}>
                          <SubmitButton className="btn sm ghost">{g.activo ? "Excluir" : "Incluir"}</SubmitButton>
                        </form>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ============================================================ CONFIGURACION */}
      {tab === "configuracion" && (
        <>
          <form action={guardarCliente.bind(null, id)} className="card stack">
            <CardHead icono={Settings} titulo="Configuración del cliente" />
            <ConfigFields v={c} />
            <div><SubmitButton pendingText="Guardando…">Guardar configuración</SubmitButton></div>
          </form>
          <details className="card danger-zone">
            <summary className="bad">Zona peligrosa: eliminar cliente</summary>
            <div className="stack" style={{ marginTop: "0.9rem" }}>
              <p className="muted small">Borra el cliente, sus grupos, publicaciones, imágenes e historial. No se puede deshacer.</p>
              <form action={eliminarCliente.bind(null, id)}>
                <SubmitButton className="btn danger" confirmar={`¿Eliminar definitivamente a ${c.nombre}?`}>
                  <Trash2 size={16} aria-hidden /> Eliminar {c.nombre}
                </SubmitButton>
              </form>
            </div>
          </details>
        </>
      )}

      {/* ============================================================ HISTORIAL */}
      {tab === "historial" && (
        <>
          <div className="card">
            <CardHead icono={History} titulo="Últimos días" />
            {(tandas ?? []).length === 0 ? (
              <Empty icono={History} titulo="Todavía no hay tandas">Aparecerán aquí cuando el bot publique.</Empty>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Día</th><th>Publicadas</th><th>Fallidas</th><th>Pendientes</th><th>Grupos nuevos</th><th>Horario</th><th>Incidencias</th></tr></thead>
                  <tbody>
                    {tandas!.map((t) => (
                      <tr key={t.fecha}>
                        <td className="nowrap"><strong>{t.fecha}</strong></td>
                        <td className="ok">{t.publicados}</td>
                        <td className={t.fallidos ? "bad" : "muted"}>{t.fallidos}</td>
                        <td>{t.pendientes}</td>
                        <td>{t.nuevos_grupos}</td>
                        <td className="muted nowrap">{t.inicio ? `${t.inicio} → ${t.fin ?? "…"}` : "—"}</td>
                        <td>{t.bloqueo || t.abortada ? <Badge tono="bad">{t.bloqueo || t.abortada}</Badge> : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <div className="card">
            <CardHead icono={ListChecks} titulo={`Últimas ${log?.length ?? 0} publicaciones`} />
            {(log ?? []).length === 0 ? (
              <Empty icono={ListChecks} titulo="Sin publicaciones registradas" />
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Hora</th><th>Grupo</th><th>Resultado</th></tr></thead>
                  <tbody>
                    {log!.map((l) => (
                      <tr key={l.id}>
                        <td className="muted nowrap">{horaCuba(l.creado)}</td>
                        <td>{l.grupo_nombre || l.grupo_url}</td>
                        <td>{l.ok ? <Badge tono="ok">Publicada</Badge> : <Badge tono="bad">{l.motivo || "Fallo"}</Badge>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </Shell>
  );
}
