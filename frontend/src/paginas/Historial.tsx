import { useState } from "react";
import { api, useCarga } from "../api";
import { Aviso, Cabecera, Campo, Cargando } from "../componentes";
import type { Referencia, Registro } from "../modelos";
import Resultado from "./Resultado";

export default function Historial({
  ejecuciones,
}: {
  ejecuciones: Referencia[];
}) {
  const [id, setId] = useState(ejecuciones.at(-1)?.id || "");
  const r = useCarga(
    () => (id ? api<Registro>(`/ejecuciones/${id}`) : Promise.resolve(null)),
    [id],
  );
  return (
    <>
      <Cabecera
        etiqueta="EJECUCIONES"
        titulo="Una decisión, su registro."
        descripcion="Cada cálculo conserva las entradas y el resultado que lo originaron."
      />
      {!ejecuciones.length ? (
        <Aviso>Todavía no hay ejecuciones guardadas.</Aviso>
      ) : (
        <>
          <div className="filtros">
            <Campo nombre="Ejecución">
              <select value={id} onChange={(e) => setId(e.target.value)}>
                {[...ejecuciones].reverse().map((e) => (
                  <option value={e.id} key={e.id}>
                    {new Date(e.fecha_utc).toLocaleString("es-AR")} ·{" "}
                    {e.tipo.replaceAll("_", " ")} · {e.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </Campo>
          </div>
          {r.cargando ? (
            <Cargando />
          ) : r.error ? (
            <Aviso tipo="error">{r.error}</Aviso>
          ) : (
            r.datos && (
              <Resultado key={r.datos.ejecucion_id} registro={r.datos} />
            )
          )}
        </>
      )}
    </>
  );
}
