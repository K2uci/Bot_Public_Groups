"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, Upload } from "lucide-react";
import { cifrarCookies } from "@/lib/crypto";
import { guardarCookies } from "@/app/actions";

// Lee cookies.json (generado por login_manual.py), las CIFRA en el navegador con la clave publica
// y solo entonces las envia al servidor. Vercel y Supabase nunca ven las cookies en claro.
export default function CookiesUpload({ clienteId }: { clienteId: string }) {
  const [estado, setEstado] = useState<{ ok: boolean; texto: string } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function subir(e: React.ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0];
    e.target.value = "";
    if (!archivo) return;
    setOcupado(true);
    setEstado(null);
    try {
      const clavePublica = process.env.NEXT_PUBLIC_COOKIE_PUBLIC_KEY;
      if (!clavePublica) throw new Error("Falta NEXT_PUBLIC_COOKIE_PUBLIC_KEY en la configuracion de la web.");
      const texto = await archivo.text();
      const cookies = JSON.parse(texto);
      const nombres = Array.isArray(cookies) ? cookies.map((c: { name?: string }) => c.name) : [];
      if (!nombres.includes("c_user") || !nombres.includes("xs")) {
        throw new Error("El archivo no parece un cookies.json de Facebook (faltan c_user y xs).");
      }
      const sobre = await cifrarCookies(texto, clavePublica);
      await guardarCookies(clienteId, sobre);
      setEstado({ ok: true, texto: "Cookies cifradas y guardadas. El bot las recogerá en menos de un minuto." });
    } catch (err) {
      setEstado({ ok: false, texto: err instanceof Error ? err.message : "Error al subir las cookies." });
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="stack">
      <label className="dropzone" style={{ cursor: ocupado ? "progress" : "pointer", flexDirection: "row" }}>
        {ocupado ? <Loader2 size={26} className="spin" aria-hidden /> : <Upload size={26} aria-hidden />}
        <span style={{ display: "flex", flexDirection: "column", gap: 2, color: "var(--text)" }}>
          <strong>{ocupado ? "Cifrando y subiendo…" : "Subir cookies.json"}</strong>
          <span className="hint">Se cifran en tu navegador antes de enviarse; el servidor nunca las ve en claro.</span>
        </span>
        <input type="file" accept=".json,application/json" onChange={subir} disabled={ocupado} style={{ display: "none" }} />
      </label>
      {estado && (
        <p className={`msg ${estado.ok ? "ok" : "error"}`} role="status">
          {estado.ok ? <CheckCircle2 size={16} aria-hidden /> : <AlertCircle size={16} aria-hidden />} {estado.texto}
        </p>
      )}
    </div>
  );
}
