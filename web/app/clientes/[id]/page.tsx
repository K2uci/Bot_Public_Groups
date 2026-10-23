import { notFound } from "next/navigation";
import Shell from "@/components/Shell";
import ConfigFields from "@/components/ConfigFields";
import CookiesUpload from "@/components/CookiesUpload";
import { requireAdmin } from "@/lib/auth";
import { horaCuba } from "@/lib/fechas";
import {
  activarCliente, activarGrupo, activarPublicacion, agregarGrupo, crearOrden, crearPublicacion,
  editarPublicacion, eliminarCliente, eliminarPublicacion, guardarCliente,
} from "@/app/actions";

export default async function ClienteDetalle({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
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

  const activos = (grupos ?? []).filter((g) => g.activo).length;

  return (
    <Shell>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>{c.nombre} <span className="suave">({c.slug})</span></h1>
        <form action={activarCliente.bind(null, id, !c.activo)}>
          <button className={c.activo ? "sec" : ""} type="submit">{c.activo ? "Pausar cliente" : "Activar cliente"}</button>
        </form>
      </div>
      {!c.activo && <p className="suave">Cliente pausado: el bot no publicará hasta que lo actives.</p>}

      {/* ------------------------------------------------ acciones */}
      <div className="card stack">
        <h2>Acciones (las ejecuta el bot en menos de un minuto)</h2>
        <div className="row">
          <form action={crearOrden.bind(null, id, "publicar_ahora")} className="row">
            <label>Máx. grupos (vacío = todos)<input name="limite" type="number" min="1" /></label>
            <button type="submit">Publicar ahora</button>
          </form>
          <form action={crearOrden.bind(null, id, "leer_grupos")}><button className="sec" type="submit">Releer grupos de la cuenta</button></form>
          <form action={crearOrden.bind(null, id, "enviar_resumen")}><button className="sec" type="submit">Enviar resumen a Telegram</button></form>
        </div>
        {(ordenes ?? []).length > 0 && (
          <table>
            <thead><tr><th>Orden</th><th>Estado</th><th>Creada</th><th>Resultado</th></tr></thead>
            <tbody>
              {ordenes!.map((o) => (
                <tr key={o.id}>
                  <td>{o.tipo}</td><td>{o.estado}</td><td>{horaCuba(o.creada)}</td><td className="suave">{o.resultado ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ------------------------------------------------ configuracion */}
      <form action={guardarCliente.bind(null, id)} className="card stack">
        <h2>Configuración</h2>
        <ConfigFields v={c} />
        <div><button type="submit">Guardar configuración</button></div>
      </form>

      {/* ------------------------------------------------ cookies */}
      <div className="card stack">
        <h2>Cookies de Facebook</h2>
        <p>
          {c.cookies_actualizadas
            ? <>Subidas el {horaCuba(c.cookies_actualizadas)} <span className="ok">✔ cifradas</span></>
            : <span className="mal">Sin cookies: el bot no puede entrar a la cuenta de este cliente.</span>}
        </p>
        <p className="suave">Se generan en tu PC con <code>python login_manual.py {c.slug}</code> (el cliente inicia sesión en la ventana de Edge).</p>
        <CookiesUpload clienteId={id} />
      </div>

      {/* ------------------------------------------------ grupos */}
      <div className="card stack">
        <h2>Grupos ({activos} activos de {grupos?.length ?? 0})</h2>
        <p className="suave">El bot revisa la cuenta al inicio de cada tanda y añade aquí los grupos nuevos. Desactiva los que no quieras usar.</p>
        <form action={agregarGrupo.bind(null, id)} className="row">
          <label>URL del grupo<input name="url" placeholder="https://www.facebook.com/groups/…" required /></label>
          <label>Nombre (opcional)<input name="nombre" /></label>
          <button className="sec" type="submit">Añadir</button>
        </form>
        <table>
          <thead><tr><th>Grupo</th><th>Detectado</th><th></th></tr></thead>
          <tbody>
            {(grupos ?? []).map((g) => (
              <tr key={g.id}>
                <td className={g.activo ? "" : "suave"}>
                  <a href={g.url} target="_blank" rel="noreferrer">{g.nombre || g.url}</a>
                </td>
                <td className="suave">{horaCuba(g.detectado)}</td>
                <td>
                  <form action={activarGrupo.bind(null, id, g.id, !g.activo)}>
                    <button className="link" type="submit">{g.activo ? "Desactivar" : "Activar"}</button>
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ------------------------------------------------ publicaciones */}
      <div className="card stack">
        <h2>Publicaciones ({(pubs ?? []).filter((p) => p.activo).length} activas)</h2>
        <p className="suave">Rotan una tras otra entre los grupos. Cada texto lleva su imagen (JPG, PNG o WEBP, máx. 4 MB).</p>
        <form action={crearPublicacion.bind(null, id)} className="stack">
          <label>Texto<textarea name="texto" required /></label>
          <label>Imagen<input name="imagen" type="file" accept="image/jpeg,image/png,image/webp" required /></label>
          <div><button type="submit">Añadir publicación</button></div>
        </form>
        {(pubs ?? []).map((p) => (
          <div key={p.id} className="pub">
            {urlDe(p.imagen_path) ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={urlDe(p.imagen_path) ?? undefined} alt="" />
            ) : <div className="suave">sin imagen</div>}
            <div className="stack">
              <form action={editarPublicacion.bind(null, id, p.id)} className="stack">
                <textarea name="texto" defaultValue={p.texto} required />
                <div className="row">
                  <button className="sec" type="submit">Guardar texto</button>
                  {!p.activo && <span className="pill">pausada</span>}
                </div>
              </form>
              <div className="row">
                <form action={activarPublicacion.bind(null, id, p.id, !p.activo)}>
                  <button className="link" type="submit">{p.activo ? "Pausar" : "Activar"}</button>
                </form>
                <form action={eliminarPublicacion.bind(null, id, p.id)}>
                  <button className="link mal" type="submit">Eliminar</button>
                </form>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ------------------------------------------------ historial */}
      <div className="card stack">
        <h2>Historial</h2>
        <table>
          <thead><tr><th>Día</th><th>Publicadas</th><th>Fallidas</th><th>Pendientes</th><th>Nuevos grupos</th><th>Horario</th><th>Incidencias</th></tr></thead>
          <tbody>
            {(tandas ?? []).map((t) => (
              <tr key={t.fecha}>
                <td>{t.fecha}</td><td className="ok">{t.publicados}</td><td className={t.fallidos ? "mal" : ""}>{t.fallidos}</td>
                <td>{t.pendientes}</td><td>{t.nuevos_grupos}</td><td className="suave">{t.inicio ?? "-"} → {t.fin ?? "…"}</td>
                <td className="mal">{t.bloqueo || t.abortada || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <details>
          <summary>Últimas {log?.length ?? 0} publicaciones</summary>
          <table>
            <thead><tr><th>Hora</th><th>Grupo</th><th>Resultado</th></tr></thead>
            <tbody>
              {(log ?? []).map((l) => (
                <tr key={l.id}>
                  <td className="suave">{horaCuba(l.creado)}</td>
                  <td>{l.grupo_nombre || l.grupo_url}</td>
                  <td>{l.ok ? <span className="ok">✔</span> : <span className="mal">✘ {l.motivo}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </div>

      {/* ------------------------------------------------ zona peligrosa */}
      <details className="card">
        <summary className="mal">Eliminar cliente</summary>
        <p className="suave">Borra el cliente, sus grupos, publicaciones, imágenes e historial. No se puede deshacer.</p>
        <form action={eliminarCliente.bind(null, id)}>
          <button className="peligro" type="submit">Sí, eliminar {c.nombre}</button>
        </form>
      </details>
    </Shell>
  );
}
