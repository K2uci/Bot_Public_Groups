"use client";

import { useFormStatus } from "react-dom";
import { Loader2 } from "lucide-react";

// Boton de envio con estado de carga; con "confirmar" pide confirmacion antes de enviar.
export default function SubmitButton({
  children,
  className = "btn primary",
  pendingText,
  confirmar,
}: {
  children: React.ReactNode;
  className?: string;
  pendingText?: string;
  confirmar?: string;
}) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      className={className}
      disabled={pending}
      onClick={(e) => {
        if (confirmar && !window.confirm(confirmar)) e.preventDefault();
      }}
    >
      {pending && <Loader2 size={16} className="spin" aria-hidden />}
      {pending && pendingText ? pendingText : children}
    </button>
  );
}
