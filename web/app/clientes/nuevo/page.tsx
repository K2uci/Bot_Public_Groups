import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import Shell from "@/components/Shell";
import ConfigFields from "@/components/ConfigFields";
import SubmitButton from "@/components/SubmitButton";
import { PageHead } from "@/components/ui";
import { crearCliente } from "@/app/actions";
import { requireAdmin } from "@/lib/auth";

export const metadata: Metadata = { title: "Nuevo cliente" };

export default async function NuevoCliente() {
  await requireAdmin();
  return (
    <Shell>
      <PageHead title="Nuevo cliente" subtitle="Nace pausado: sube sus cookies, revisa grupos y publicaciones y luego actívalo.">
        <Link href="/clientes" className="btn">
          <ArrowLeft size={16} aria-hidden /> Volver
        </Link>
      </PageHead>
      <form action={crearCliente} className="card stack" style={{ maxWidth: 820 }}>
        <label>
          Identificador
          <input name="slug" pattern="[a-z0-9_\-]{2,40}" placeholder="ej: juan-perez" required />
          <span className="hint">Solo a-z, 0-9, guion y guion bajo (2 a 40). No se puede cambiar después.</span>
        </label>
        <ConfigFields />
        <div>
          <SubmitButton pendingText="Creando…">Crear cliente</SubmitButton>
        </div>
      </form>
    </Shell>
  );
}
