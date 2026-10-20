import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, useCarga } from "../api";
import { Aviso, Cabecera, Campo, Cargando, Panel, Tabla } from "../componentes";
import { metodos, numero } from "../modelos";
import type { Referencia, Registro, Metodo } from "../modelos";

export default function Evaluacion({
  ejecuciones,
}: {
  ejecuciones: Referencia[];
}) {
  const lista = ejecuciones.filter((e) => e.tipo === "evaluacion_predictiva");
  const [id, setId] = useState(lista.at(-1)?.id || "");
  const [pid, setPid] = useState("P01");
  const [h, setH] = useState("1");
  const [metric, setMetric] = useState("mae");
  const r = useCarga(
    () => (id ? api<Registro>(`/ejecuciones/${id}`) : Promise.resolve(null)),
    [id],
  );
  const p = r.datos?.resultado.productos.find(
    (p: any) => p.producto_id === pid,
  );
  const grupos =
    p?.metricas.filter((m: any) => m.horizonte === Number(h)) || [];
  const grafico = grupos.map((m: any) => ({
    nombre: metodos[m.metodo as Metodo],
    valor: m[metric],
  }));
  const columnas = [
    {
      id: "metodo",
      titulo: "Método",
      mostrar: (m: any) => metodos[m.metodo as Metodo],
    },
    {
      id: "mae",
      titulo: "MAE",
      numero: true,
      mostrar: (m: any) => numero(m.mae, 3),
    },
    {
      id: "rmse",
      titulo: "RMSE",
      numero: true,
      mostrar: (m: any) => numero(m.rmse, 3),
    },
    {
      id: "mase",
      titulo: "MASE",
      numero: true,
      mostrar: (m: any) =>
        m.mase == null
          ? m.n_predicciones === 0
            ? "No aplicable: sin casos"
            : m.n_pares_escala_max === 0
              ? "No aplicable: sin pares"
              : "No aplicable: escala nula"
          : numero(m.mase, 3),
    },
    { id: "n_origenes", titulo: "Orígenes", numero: true },
  ];
  return (
    <>
      <Cabecera
        etiqueta="EVALUACIÓN PREDICTIVA"
        titulo="Comparar antes de confiar."
        descripcion="Los tres métodos se evalúan sobre los mismos casos por producto y horizonte."
      />
      {!lista.length ? (
        <Aviso>
          La evaluación se ejecuta siguiendo el manual. Sus resultados
          aparecerán aquí cuando termine.
        </Aviso>
      ) : (
        <>
          <div className="filtros">
            <Campo nombre="Evaluación">
              <select value={id} onChange={(e) => setId(e.target.value)}>
                {lista.map((e) => (
                  <option key={e.id} value={e.id}>
                    {new Date(e.fecha_utc).toLocaleDateString("es-AR")} ·{" "}
                    {e.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo nombre="Producto">
              <select value={pid} onChange={(e) => setPid(e.target.value)}>
                {Array.from({ length: 7 }, (_, i) => `P0${i + 1}`).map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </Campo>
            <Campo nombre="Horizonte">
              <select value={h} onChange={(e) => setH(e.target.value)}>
                {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                  <option key={n} value={n}>
                    {n} día{n > 1 ? "s" : ""}
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
            p && (
              <>
                <Panel
                  titulo="Error por método"
                  detalle={
                    <select
                      aria-label="Métrica del gráfico"
                      value={metric}
                      onChange={(e) => setMetric(e.target.value)}
                    >
                      {["mae", "rmse", "mase"].map((m) => (
                        <option key={m} value={m}>
                          {m.toUpperCase()}
                        </option>
                      ))}
                    </select>
                  }
                >
                  <div className="grafico">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={grafico}
                        barSize={54}
                        margin={{ top: 20, right: 25, left: -20, bottom: 4 }}
                      >
                        <CartesianGrid vertical={false} stroke="var(--linea)" />
                        <XAxis
                          dataKey="nombre"
                          axisLine={false}
                          tickLine={false}
                          tick={{ fontSize: 12, fill: "var(--suave)" }}
                        />
                        <YAxis
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "var(--suave)", fontSize: 12 }}
                        />
                        <Tooltip
                          formatter={(v: any) => numero(v, 3)}
                          contentStyle={{
                            background: "var(--panel)",
                            color: "var(--texto)",
                            border: "1px solid var(--linea)",
                            borderRadius: 8,
                          }}
                        />
                        <Bar
                          dataKey="valor"
                          name={metric.toUpperCase()}
                          fill="var(--acento)"
                          radius={[5, 5, 0, 0]}
                          isAnimationActive={false}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="nota">
                    Menor error es mejor. MAE y RMSE se expresan en unidades
                    vendidas; MASE usa una escala calculada con el
                    entrenamiento.
                  </p>
                  <Tabla filas={grupos} columnas={columnas} />
                </Panel>
                {grupos.some((m: any) => m.exploratoria) && (
                  <Aviso tipo="stock">
                    Este horizonte tiene menos de 14 orígenes: su comparación es
                    exploratoria.
                  </Aviso>
                )}
                <div className="dos-columnas">
                  <Panel titulo="Configuración">
                    <p className="prosa">
                      {p.estado_configuracion === "seleccionada_por_validacion"
                        ? "Seleccionada mediante validación temporal."
                        : "Prefijada por cobertura insuficiente de validación."}
                    </p>
                    <dl className="ficha">
                      <dt>Árboles</dt>
                      <dd>{p.parametros.n_estimators}</dd>
                      <dt>Profundidad máxima</dt>
                      <dd>{p.parametros.max_depth}</dd>
                      <dt>Semilla</dt>
                      <dd>{p.parametros.random_state}</dd>
                    </dl>
                  </Panel>
                  <Panel titulo="Alcance del resultado">
                    <p className="prosa">
                      Una mejora de precisión no demuestra ahorro, reducción de
                      desperdicio ni mejor inventario real.
                    </p>
                    <p className="nota">
                      Se conservan los resultados donde Random Forest tiene
                      mayor error que las referencias.
                    </p>
                  </Panel>
                </div>
                <details>
                  <summary>
                    Sensibilidad con orígenes separados al menos siete días
                  </summary>
                  <Tabla
                    filas={p.sensibilidad.filter(
                      (m: any) => m.horizonte === Number(h),
                    )}
                    columnas={columnas}
                  />
                  <p className="nota">
                    La separación no demuestra independencia estadística.
                  </p>
                  {p.bloques_p07 && (
                    <Aviso>
                      Bloques completos de P07:{" "}
                      {p.bloques_p07.n_bloques_completos}. Un solo bloque no
                      permite comprobar robustez al retirarlo.
                    </Aviso>
                  )}
                </details>
                <details>
                  <summary>Casos excluidos del horizonte</summary>
                  <Tabla
                    filas={p.casos.filter(
                      (c: any) => c.horizonte === Number(h) && !c.evaluable,
                    )}
                    columnas={[
                      { id: "origen", titulo: "Origen" },
                      { id: "fecha_objetivo", titulo: "Fecha objetivo" },
                      {
                        id: "motivos",
                        titulo: "Motivos",
                        mostrar: (c) =>
                          c.motivos.join(" · ").replaceAll("_", " "),
                      },
                    ]}
                  />
                </details>
              </>
            )
          )}
        </>
      )}
    </>
  );
}
