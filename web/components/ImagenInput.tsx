"use client";

import { useState } from "react";

const MAX_BYTES = 4 * 1024 * 1024;
const TIPOS = ["image/jpeg", "image/png", "image/webp"];

// Selector de imagen que avisa al elegir el archivo (tipo y peso) en vez de fallar despues al enviar.
// La validacion real sigue en el servidor (crearPublicacion); esto solo mejora la experiencia.
export default function ImagenInput({ name = "imagen" }: { name?: string }) {
  const [aviso, setAviso] = useState("");

  return (
    <>
      <input
        name={name}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        required
        onChange={(e) => {
          const archivo = e.currentTarget.files?.[0];
          let msg = "";
          if (archivo) {
            if (!TIPOS.includes(archivo.type)) msg = "Solo se admiten imágenes JPG, PNG o WEBP.";
            else if (archivo.size > MAX_BYTES) msg = `La imagen pesa ${(archivo.size / 1048576).toFixed(1)} MB y el máximo es 4 MB.`;
          }
          e.currentTarget.setCustomValidity(msg);
          setAviso(msg);
          if (msg) e.currentTarget.reportValidity();
        }}
      />
      {aviso && (
        <span className="hint" style={{ color: "var(--bad)" }} role="alert">
          {aviso}
        </span>
      )}
    </>
  );
}
