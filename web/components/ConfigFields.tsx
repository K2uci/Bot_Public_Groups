import { DIAS } from "@/lib/fechas";

type Valores = {
  nombre?: string;
  hora_inicio?: string;
  espera_min?: number | null;
  espera_max?: number | null;
  dias_semana?: number[] | null;
  max_grupos_dia?: number | null;
  tg_chat_id?: string | null;
};

// Campos de configuracion de un cliente (compartidos por "crear" y "editar").
// El intervalo entre publicaciones es obligatorio: lo decide cada cliente.
export default function ConfigFields({ v = {} }: { v?: Valores }) {
  return (
    <>
      <div className="grid cols-2">
        <label>
          Nombre
          <input name="nombre" defaultValue={v.nombre ?? ""} required />
        </label>
        <label>
          Hora de inicio
          <input name="hora_inicio" type="time" defaultValue={v.hora_inicio ?? "10:00"} required />
          <span className="hint">Hora de Cuba.</span>
        </label>
        <label>
          Espera mínima entre publicaciones
          <input name="espera_min" type="number" step="0.5" min="1" defaultValue={v.espera_min ?? ""} required />
          <span className="hint">Minutos. Lo decide el cliente.</span>
        </label>
        <label>
          Espera máxima
          <input name="espera_max" type="number" step="0.5" min="1" defaultValue={v.espera_max ?? ""} required />
          <span className="hint">Minutos. Cada pausa es aleatoria entre ambas.</span>
        </label>
        <label>
          Máximo de grupos por día
          <input name="max_grupos_dia" type="number" min="1" defaultValue={v.max_grupos_dia ?? ""} placeholder="Todos" />
          <span className="hint">Vacío = todos los grupos. Con tope, rota cada día.</span>
        </label>
        <label>
          Chat de Telegram del cliente
          <input name="tg_chat_id" defaultValue={v.tg_chat_id ?? ""} placeholder="Opcional" />
          <span className="hint">Recibe su resumen diario.</span>
        </label>
      </div>
      <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="small muted" style={{ fontWeight: 600, marginBottom: 6, padding: 0 }}>
          Días de publicación (ninguno marcado = todos)
        </legend>
        <div className="row center">
          {DIAS.map((d, i) => (
            <label key={d} className="check">
              <input type="checkbox" name="dias" value={i} defaultChecked={v.dias_semana?.includes(i) ?? false} />
              {d}
            </label>
          ))}
        </div>
      </fieldset>
    </>
  );
}
