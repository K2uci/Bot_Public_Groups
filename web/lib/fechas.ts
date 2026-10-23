// Todo el negocio funciona en hora de Cuba (el servidor de Vercel esta en UTC).
const ZONA = "America/Havana";

export function hoyCuba(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: ZONA }); // YYYY-MM-DD
}

export function horaCuba(iso: string | null | undefined): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("es-ES", {
    timeZone: ZONA,
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const DIAS = ["L", "M", "X", "J", "V", "S", "D"];

// Segundos transcurridos desde una fecha ISO (Infinity si no hay fecha)
export function segundosDesde(iso: string | null | undefined): number {
  return iso ? (Date.now() - new Date(iso).getTime()) / 1000 : Infinity;
}
