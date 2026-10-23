import "server-only";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

// Exige sesion iniciada Y que el usuario este en la tabla "admins".
// Se llama al principio de cada pagina y de cada server action (nunca confiar solo en el proxy).
export async function requireAdmin() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: esAdmin } = await supabase.rpc("es_admin");
  if (!esAdmin) {
    await supabase.auth.signOut();
    redirect("/login?error=permiso");
  }
  return { supabase, user };
}
