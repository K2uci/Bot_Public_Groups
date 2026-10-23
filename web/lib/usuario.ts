// Supabase Auth identifica a las personas por correo. Como el panel entra con NOMBRE DE USUARIO,
// cada usuario se guarda con un correo interno ficticio derivado de su nombre (nunca se envian correos).
export const DOMINIO_INTERNO = "usuarios.invalid";
export const USUARIO_RE = /^[a-z0-9._-]{3,32}$/;

export function correoDeUsuario(usuario: string): string {
  return `${usuario.trim().toLowerCase()}@${DOMINIO_INTERNO}`;
}

export function usuarioDeCorreo(correo: string | undefined | null): string {
  return (correo ?? "").replace(`@${DOMINIO_INTERNO}`, "");
}
