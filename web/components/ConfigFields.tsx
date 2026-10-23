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
      <div className="grid2">
        <label>
          Nombre
          <input name="nombre" defaultValue={v.nombre ?? ""} required />
        </label>
        <label>
          Hora de inicio (hora de Cuba)
          <input name="hora_inicio" type="time" defaultValue={v.hora_inicio ?? "10:00"} required />
        </label>
        <label>
          Espera mínima entre publicaciones (min)
          <input name="espera_min" type="number" step="0.5" min="1" defaultValue={v.espera_min ?? ""} required />
        </label>
        <label>
          Espera máxima (min)
          <input name="espera_max" type="number" step="0.5" min="1" defaultValue={v.espera_max ?? ""} required />
        </label>
        <label>
          Máximo de grupos por día (vacío = todos)
          <input name="max_grupos_dia" type="number" min="1" defaultValue={v.max_grupos_dia ?? ""} />
        </label>
        <label>
          Chat de Telegram del cliente (opcional)
          <input name="tg_chat_id" defaultValue={v.tg_chat_id ?? ""} />
        </label>
      </div>
      <div className="row">
        <span className="suave">Días (ninguno marcado = todos):</span>
        {DIAS.map((d, i) => (
          <label key={d} className="inline">
            <input type="checkbox" name="dias" value={i} defaultChecked={v.dias_semana?.includes(i) ?? false} />
            {d}
          </label>
        ))}
      </div>
    </>
  );
}
