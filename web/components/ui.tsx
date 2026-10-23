import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export type Tono = "muted" | "ok" | "bad" | "warn" | "primary";

export function PageHead({ title, subtitle, children }: { title: string; subtitle?: ReactNode; children?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children && <div className="page-actions">{children}</div>}
    </div>
  );
}

export function Badge({ tono = "muted", punto, pulso, children }: { tono?: Tono; punto?: boolean; pulso?: boolean; children: ReactNode }) {
  return (
    <span className={`badge ${tono === "muted" ? "" : tono}`}>
      {punto && <span className={`dot ${pulso ? "pulse" : ""}`} aria-hidden />}
      {children}
    </span>
  );
}

export function Stat({ icono: Icono, tono, valor, etiqueta }: { icono: LucideIcon; tono?: "ok" | "bad" | "warn"; valor: ReactNode; etiqueta: ReactNode }) {
  return (
    <div className="stat">
      <div className={`ico ${tono ?? ""}`}>
        <Icono size={21} aria-hidden />
      </div>
      <div>
        <div className="num">{valor}</div>
        <div className="lbl">{etiqueta}</div>
      </div>
    </div>
  );
}

export function CardHead({ icono: Icono, titulo, children }: { icono?: LucideIcon; titulo: string; children?: ReactNode }) {
  return (
    <div className="card-head">
      <h2>
        {Icono && <Icono size={18} aria-hidden />}
        {titulo}
      </h2>
      {children}
    </div>
  );
}

export function Empty({ icono: Icono, titulo, children }: { icono: LucideIcon; titulo: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <Icono size={34} aria-hidden />
      <strong style={{ color: "var(--text)" }}>{titulo}</strong>
      {children && <div className="small">{children}</div>}
    </div>
  );
}
