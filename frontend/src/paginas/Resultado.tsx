import { useState } from "react";
import { ArrowDownToLine } from "lucide-react";
import { api, descargarJSON, useCarga } from "../api";
import { Aviso, Cargando, Panel, Tabla } from "../componentes";
import { etiquetaResultado, fechaCompleta, numero } from "../modelos";
import type { Registro } from "../modelos";

export default function Resultado({ registro }: { registro: Registro }) {
  const [insumo, setInsumo] = useState(
    registro.resultado.alertas?.[0]?.insumo_id ||
      registro.entradas.recetario?.insumos[0]?.insumo_id ||
      "",
  );
  const balance = ["planificacion", "balance"].includes(registro.tipo);
  const detalle = useCarga(
    () =>
      balance && insumo
        ? api<any>(`/ejecuciones/${registro.ejecucion_id}/insumos/${insumo}`)
        : Promise.resolve(null),
    [registro.ejecucion_id, insumo],
  );
  return (
    <div className="resultado">
      <div className="resultado-id">
        <span>
          Guardado · {new Date(registro.fecha_utc).toLocaleString("es-AR")}
        </span>
        <button
          className="texto-boton"
          onClick={() =>
            descargarJSON(registro, `ejecucion-${registro.ejecucion_id}.json`)
          }
        >
          <ArrowDownToLine size={14} /> Descargar registro
        </button>
      </div>
      {balance ? (
        <>
          <Aviso tipo={registro.resultado.alertas.length ? "stock" : "ok"}>
            <strong>
              {etiquetaResultado(registro.resultado.alertas.length)}
            </strong>
            <p>
              Es un resultado del inventario sintético, no un fallo del modelo.
              Revisá las existencias y las entradas previstas.
            </p>
          </Aviso>
          {registro.contexto.pronosticos && (
            <Panel titulo="Cantidades previstas">
              <Tabla
                filas={registro.contexto.pronosticos}
                columnas={[
                  { id: "producto_id", titulo: "Producto" },
                  {
                    id: "fecha",
                    titulo: "Fecha",
                    mostrar: (r) => fechaCompleta(r.fecha),
                  },
                  {
                    id: "cantidad",
                    titulo: "Unidades estimadas",
                    numero: true,
                    mostrar: (r) => numero(r.cantidad),
                  },
                ]}
              />
            </Panel>
          )}
          <Panel
            titulo="Detalle por insumo"
            detalle={
              <select
                aria-label="Insumo del detalle"
                value={insumo}
                onChange={(e) => setInsumo(e.target.value)}
              >
                {registro.entradas.recetario.insumos.map((i: any) => (
                  <option key={i.insumo_id} value={i.insumo_id}>
                    {i.nombre} · {i.unidad}
                  </option>
                ))}
              </select>
            }
          >
            {detalle.cargando ? (
              <Cargando />
            ) : detalle.error ? (
              <Aviso tipo="error">{detalle.error}</Aviso>
            ) : (
              detalle.datos && (
                <>
                  <Tabla
                    filas={detalle.datos.balance}
                    columnas={[
                      {
                        id: "fecha",
                        titulo: "Fecha",
                        mostrar: (r) => fechaCompleta(r.fecha),
                      },
                      {
                        id: "existencia_antes",
                        titulo: "Antes",
                        numero: true,
                        mostrar: (r) => numero(r.existencia_antes),
                      },
                      {
                        id: "entradas",
                        titulo: "Entradas",
                        numero: true,
                        mostrar: (r) => numero(r.entradas),
                      },
                      {
                        id: "consumo",
                        titulo: "Consumo",
                        numero: true,
                        mostrar: (r) => numero(r.consumo),
                      },
                      {
                        id: "saldo",
                        titulo: "Saldo",
                        numero: true,
                        mostrar: (r) => (
                          <span
                            className={Number(r.saldo) < 0 ? "negativo" : ""}
                          >
                            {numero(r.saldo)}
                          </span>
                        ),
                      },
                    ]}
                  />
                  <details>
                    <summary>Aportes de cada producto y componente</summary>
                    <Tabla
                      filas={detalle.datos.aportes}
                      columnas={[
                        { id: "producto_id", titulo: "Producto" },
                        {
                          id: "fecha",
                          titulo: "Fecha",
                          mostrar: (r) => fechaCompleta(r.fecha),
                        },
                        { id: "componente", titulo: "Componente" },
                        {
                          id: "consumo",
                          titulo: "Consumo",
                          numero: true,
                          mostrar: (r) => `${numero(r.consumo)} ${r.unidad}`,
                        },
                      ]}
                    />
                  </details>
                </>
              )
            )}
          </Panel>
        </>
      ) : registro.tipo === "consulta_pronostico" ? (
        <Panel titulo="Próximos siete días">
          <Tabla
            filas={registro.resultado.pronosticos}
            columnas={[
              {
                id: "fecha",
                titulo: "Fecha",
                mostrar: (r) => fechaCompleta(r.fecha),
              },
              {
                id: "cantidad",
                titulo: "Unidades estimadas",
                numero: true,
                mostrar: (r) => numero(r.cantidad),
              },
              {
                id: "causa",
                titulo: "Disponibilidad",
                mostrar: (r) =>
                  r.disponible ? "Pronóstico disponible" : r.causa,
              },
            ]}
          />
        </Panel>
      ) : (
        <Aviso>
          Esta ejecución corresponde a{" "}
          {registro.tipo === "seleccion_modelos"
            ? "la selección de configuraciones"
            : "la evaluación predictiva"}
          . Podés consultar sus métricas en Evaluación y descargar el registro
          completo.
        </Aviso>
      )}
      <details className="procedencia">
        <summary>Procedencia y reproducción</summary>
        <dl className="ficha">
          <dt>ID</dt>
          <dd className="mono">{registro.ejecucion_id}</dd>
          <dt>Huella del contenido</dt>
          <dd className="mono">{registro.huella_contenido}</dd>
          <dt>Método</dt>
          <dd>{registro.contexto.metodo || registro.tipo}</dd>
          <dt>Origen</dt>
          <dd>
            {registro.contexto.origen || "Según el protocolo de evaluación"}
          </dd>
        </dl>
      </details>
    </div>
  );
}
