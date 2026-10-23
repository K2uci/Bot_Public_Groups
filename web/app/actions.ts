"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { requireAdmin } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";
import type { SobreCifrado } from "@/lib/crypto";
import { USUARIO_RE, correoDeUsuario } from "@/lib/usuario";

// ---------------------------------------------------------------- sesion
export async function login(formData: FormData) {
  const usuario = String(formData.get("usuario") ?? "").trim().toLowerCase();
  // Mismo mensaje para "usuario inexistente" y "contraseña incorrecta": no se revela cuales usuarios existen
  if (!USUARIO_RE.test(usuario)) redirect("/login?error=credenciales");
  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({
    email: correoDeUsuario(usuario),
    password: String(formData.get("password") ?? ""),
  });
  if (error) {
    // Solo codigo y estado, nunca la contrasena: queda en los logs del servidor para diagnosticar
    console.error("login fallido:", error.status, error.code);
    redirect("/login?error=credenciales");
  }
  redirect("/");
}

export async function logout() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}

export async function cambiarPassword(formData: FormData) {
  const { supabase } = await requireAdmin();
  const nueva = String(formData.get("nueva") ?? "");
  if (nueva !== String(formData.get("repetir") ?? "")) redirect("/cuenta?error=distintas");
  if (nueva.length < 12) redirect("/cuenta?error=corta");
  const { error } = await supabase.auth.updateUser({ password: nueva });
  if (error) redirect("/cuenta?error=fallo");
  redirect("/cuenta?ok=1");
}

// ---------------------------------------------------------------- clientes
function num(v: FormDataEntryValue | null): number | null {
  const n = Number(String(v ?? "").replace(",", "."));
  return Number.isFinite(n) && String(v ?? "").trim() !== "" ? n : null;
}

function leerConfig(formData: FormData) {
  const espera_min = num(formData.get("espera_min"));
  const espera_max = num(formData.get("espera_max"));
  // El intervalo lo decide el cliente: es obligatorio y no hay valor por defecto
  if (espera_min === null || espera_max === null || espera_min < 1 || espera_min > espera_max) {
    throw new Error("Indica el intervalo entre publicaciones en minutos (minimo 1, y minimo <= maximo).");
  }
  const dias = formData.getAll("dias").map(Number).filter((d) => d >= 0 && d <= 6);
  const maxGrupos = num(formData.get("max_grupos_dia"));
  return {
    nombre: String(formData.get("nombre") ?? "").trim(),
    hora_inicio: String(formData.get("hora_inicio") ?? "10:00"),
    espera_min,
    espera_max,
    dias_semana: dias.length === 0 || dias.length === 7 ? null : dias,
    max_grupos_dia: maxGrupos && maxGrupos > 0 ? Math.floor(maxGrupos) : null,
    tg_chat_id: String(formData.get("tg_chat_id") ?? "").trim() || null,
  };
}

export async function crearCliente(formData: FormData) {
  const { supabase } = await requireAdmin();
  const slug = String(formData.get("slug") ?? "").trim().toLowerCase();
  const cfg = leerConfig(formData);
  if (!/^[a-z0-9_-]{2,40}$/.test(slug)) throw new Error("El identificador solo admite a-z, 0-9, - y _ (2 a 40).");
  if (!cfg.nombre) throw new Error("Falta el nombre.");
  const { data, error } = await supabase
    .from("clientes")
    .insert({ slug, ...cfg, activo: false })
    .select("id")
    .single();
  if (error) throw new Error(error.message);
  revalidatePath("/clientes");
  redirect(`/clientes/${data.id}`);
}

export async function guardarCliente(id: string, formData: FormData) {
  const { supabase } = await requireAdmin();
  const { error } = await supabase.from("clientes").update(leerConfig(formData)).eq("id", id);
  if (error) throw new Error(error.message);
  revalidatePath(`/clientes/${id}`);
}

export async function activarCliente(id: string, activo: boolean) {
  const { supabase } = await requireAdmin();
  const { error } = await supabase.from("clientes").update({ activo }).eq("id", id);
  if (error) throw new Error(error.message);
  revalidatePath(`/clientes/${id}`);
  revalidatePath("/");
}

export async function eliminarCliente(id: string) {
  const { supabase } = await requireAdmin();
  // Borra tambien las imagenes del cliente en el almacenamiento
  const { data: pubs } = await supabase.from("publicaciones").select("imagen_path").eq("cliente_id", id);
  if (pubs?.length) await supabase.storage.from("imagenes").remove(pubs.map((p) => p.imagen_path));
  const { error } = await supabase.from("clientes").delete().eq("id", id);
  if (error) throw new Error(error.message);
  revalidatePath("/clientes");
  redirect("/clientes");
}

// El navegador ya cifro las cookies: el servidor solo guarda el sobre, nunca las ve en claro.
export async function guardarCookies(id: string, sobre: SobreCifrado) {
  const { supabase } = await requireAdmin();
  if (sobre?.v !== 1 || !sobre.k || !sobre.iv || !sobre.ct) throw new Error("Sobre de cookies invalido.");
  const { error } = await supabase
    .from("clientes")
    .update({ cookies_cifradas: sobre, cookies_actualizadas: new Date().toISOString() })
    .eq("id", id);
  if (error) throw new Error(error.message);
  revalidatePath(`/clientes/${id}`);
}

// ---------------------------------------------------------------- grupos
export async function agregarGrupo(clienteId: string, formData: FormData) {
  const { supabase } = await requireAdmin();
  const url = String(formData.get("url") ?? "").trim().split("?")[0].replace(/\/$/, "");
  if (!/^https:\/\/(www\.)?facebook\.com\/groups\/[^/]+$/.test(url)) {
    throw new Error("La URL debe ser https://www.facebook.com/groups/...");
  }
  const nombre = String(formData.get("nombre") ?? "").trim() || null;
  const { error } = await supabase
    .from("grupos")
    .upsert({ cliente_id: clienteId, url, nombre }, { onConflict: "cliente_id,url", ignoreDuplicates: true });
  if (error) throw new Error(error.message);
  revalidatePath(`/clientes/${clienteId}`);
}

export async function activarGrupo(clienteId: string, grupoId: string, activo: boolean) {
  const { supabase } = await requireAdmin();
  const { error } = await supabase.from("grupos").update({ activo }).eq("id", grupoId).eq("cliente_id", clienteId);
  if (error) throw new Error(error.message);
  revalidatePath(`/clientes/${clienteId}`);
}

// ---------------------------------------------------------------- publicaciones
const TIPOS_IMAGEN: Record<string, string> = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp" };

export async function crearPublicacion(clienteId: string, formData: FormData) {
  const { supabase } = await requireAdmin();
  const texto = String(formData.get("texto") ?? "").trim();
  const archivo = formData.get("imagen");
  if (!texto) throw new Error("Falta el texto de la publicacion.");
  if (!(archivo instanceof File) || archivo.size === 0) throw new Error("Falta la imagen.");
  const ext = TIPOS_IMAGEN[archivo.type];
  if (!ext) throw new Error("La imagen debe ser JPG, PNG o WEBP.");
  if (archivo.size > 4 * 1024 * 1024) throw new Error("La imagen supera 4 MB.");

  const path = `${clienteId}/${crypto.randomUUID()}.${ext}`;
  const { error: errSubida } = await supabase.storage.from("imagenes").upload(path, archivo, { contentType: archivo.type });
  if (errSubida) throw new Error(errSubida.message);

  const { error } = await supabase.from("publicaciones").insert({ cliente_id: clienteId, texto, imagen_path: path });
  if (error) {
    await supabase.storage.from("imagenes").remove([path]);
    throw new Error(error.message);
  }
  revalidatePath(`/clientes/${clienteId}`);
}

export async function editarPublicacion(clienteId: string, pubId: string, formData: FormData) {
  const { supabase } = await requireAdmin();
  const texto = String(formData.get("texto") ?? "").trim();
  if (!texto) throw new Error("El texto no puede quedar vacio.");
  const { error } = await supabase
    .from("publicaciones")
    .update({ texto, actualizada: new Date().toISOString() })
    .eq("id", pubId)
    .eq("cliente_id", clienteId);
  if (error) throw new Error(error.message);
  revalidatePath(`/clientes/${clienteId}`);
}

export async function activarPublicacion(clienteId: string, pubId: string, activo: boolean) {
  const { supabase } = await requireAdmin();
  const { error } = await supabase
    .from("publicaciones")
    .update({ activo, actualizada: new Date().toISOString() })
    .eq("id", pubId)
    .eq("cliente_id", clienteId);
  if (error) throw new Error(error.message);
  revalidatePath(`/clientes/${clienteId}`);
}

export async function eliminarPublicacion(clienteId: string, pubId: string) {
  const { supabase } = await requireAdmin();
  const { data } = await supabase.from("publicaciones").select("imagen_path").eq("id", pubId).eq("cliente_id", clienteId).single();
  const { error } = await supabase.from("publicaciones").delete().eq("id", pubId).eq("cliente_id", clienteId);
  if (error) throw new Error(error.message);
  if (data?.imagen_path) await supabase.storage.from("imagenes").remove([data.imagen_path]);
  revalidatePath(`/clientes/${clienteId}`);
}

// ---------------------------------------------------------------- ordenes al bot
export async function crearOrden(clienteId: string, tipo: "publicar_ahora" | "leer_grupos" | "enviar_resumen", formData?: FormData) {
  const { supabase } = await requireAdmin();
  const limite = formData ? num(formData.get("limite")) : null;
  const parametros = tipo === "publicar_ahora" && limite && limite > 0 ? { limite: Math.floor(limite) } : {};
  const { error } = await supabase.from("ordenes").insert({ cliente_id: clienteId, tipo, parametros });
  if (error) throw new Error(error.message);
  revalidatePath(`/clientes/${clienteId}`);
}
