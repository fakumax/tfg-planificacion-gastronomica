import { useState } from "react";
import { ArrowDownToLine, CalendarDays } from "lucide-react";
import { api, descargarJSON, parametros, useCarga } from "../api";
import {
  Aviso,
  Cabecera,
  Campo,
  Cargando,
  Dato,
  Grafico,
  Panel,
  Tabla,
} from "../componentes";
import { fechaCompleta, numero, prepararSerie } from "../modelos";
import type { Producto, Ventas as ConsultaVentas } from "../modelos";

export default function Ventas({
  importacion,
  productos,
}: {
  importacion: string;
  productos: Producto[];
}) {
  const [producto, setProducto] = useState(productos[0]?.producto_id || "P01");
  const anio = productos[0]?.anio || 2025;
  const [desde, setDesde] = useState(`${anio}-11-01`);
  const [hasta, setHasta] = useState(`${anio}-11-30`);
  const [consulta, setConsulta] = useState({ producto, desde, hasta });
  const { datos, error, cargando } = useCarga(
    () =>
      api<ConsultaVentas>("/ventas" + parametros({ importacion, ...consulta })),
    [importacion, consulta],
  );
  const [tabla, setTabla] = useState(false);
  return (
    <>
      <Cabecera
        etiqueta="HISTORIAL DE VENTAS"
        titulo="Cada día cuenta."
        descripcion="Consultá lo registrado y reconocé los días que necesitan una interpretación."
      >
        <button
          className="boton secundario"
          disabled={!datos}
          onClick={() => descargarJSON(datos, "consulta-ventas.json")}
        >
          <ArrowDownToLine size={16} /> Exportar consulta
        </button>
      </Cabecera>
      <form
        className="filtros"
        onSubmit={(e) => {
          e.preventDefault();
          setConsulta({ producto, desde, hasta });
        }}
      >
        <Campo nombre="Producto">
          <select
            value={producto}
            onChange={(e) => setProducto(e.target.value)}
          >
            {productos.map((p) => (
              <option key={p.producto_id} value={p.producto_id}>
                {p.producto_id} · {p.nombre_modelado}
              </option>
            ))}
          </select>
        </Campo>
        <Campo nombre="Desde">
          <input
            aria-label="Desde"
            type="date"
            onInput={(e) => setDesde(e.currentTarget.value)}
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            required
          />
        </Campo>
        <Campo nombre="Hasta">
          <input
            aria-label="Hasta"
            type="date"
            onInput={(e) => setHasta(e.currentTarget.value)}
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            required
          />
        </Campo>
        <button className="boton" disabled={cargando}>
          Consultar período
        </button>
      </form>
      {error && <Aviso tipo="error">{error}</Aviso>}
      {cargando ? (
        <Cargando />
      ) : (
        datos && (
          <>
            <div className="datos-tres">
              <Dato
                etiqueta="Unidades registradas"
                valor={numero(datos.total_observado, 0)}
                detalle={
                  datos.incompleta
                    ? "Suma de las fechas con registro"
                    : "Total del período seleccionado"
                }
              />
              <Dato
                etiqueta="Fechas con registro"
                valor={numero(datos.dias_observados, 0)}
                detalle={`De ${datos.diarias.length} fechas consultadas`}
              />
              <Dato
                etiqueta="Fechas sin fila"
                valor={numero(datos.dias_sin_fila, 0)}
                detalle="Se mantienen diferenciadas de cero"
              />
            </div>
            <Panel
              titulo="Ritmo diario"
              detalle={
                <span className="etiqueta">
                  <CalendarDays size={13} />
                  {fechaCompleta(consulta.desde)} —{" "}
                  {fechaCompleta(consulta.hasta)}
                </span>
              }
            >
              <div className="leyenda">
                <i /> Unidades vendidas · {datos.producto.producto_id}
              </div>
              <Grafico datos={prepararSerie(datos.diarias)} />
              <div className="pie-grafico">
                <span>{datos.producto.nombre_modelado}</span>
                <button
                  className="texto-boton"
                  onClick={() => setTabla(!tabla)}
                >
                  {tabla ? "Ocultar" : "Ver"} registros
                </button>
              </div>
              {tabla && (
                <Tabla
                  columnas={[
                    {
                      id: "fecha",
                      titulo: "Fecha",
                      mostrar: (r) => fechaCompleta(r.fecha),
                    },
                    {
                      id: "cantidad",
                      titulo: "Unidades",
                      numero: true,
                      mostrar: (r) => numero(r.cantidad, 0),
                    },
                    {
                      id: "estado",
                      titulo: "Registro",
                      mostrar: (r) => (
                        <span
                          className={`etiqueta ${r.cantidad == null ? "ambar" : "verde"}`}
                        >
                          {r.cantidad == null ? "Sin fila" : "Observado"}
                        </span>
                      ),
                    },
                  ]}
                  filas={datos.diarias}
                />
              )}
            </Panel>
            <div className="dos-columnas">
              <Panel titulo="Sobre esta consulta">
                <dl className="ficha">
                  <dt>Producto original</dt>
                  <dd>{datos.producto.producto_original}</dd>
                  <dt>Establecimiento</dt>
                  <dd>{datos.producto.local_original}</dd>
                  <dt>Naturaleza</dt>
                  <dd>Ventas observadas</dd>
                </dl>
              </Panel>
              <Panel titulo="Cómo leer los espacios">
                <p className="prosa">
                  Una fecha sin fila aparece como un corte. El criterio vigente
                  no la transforma automáticamente en cero ventas.
                </p>
                <p className="nota">
                  Esta interpretación sigue pendiente de contrastar con la
                  documentación de la fuente.
                </p>
              </Panel>
            </div>
          </>
        )
      )}
    </>
  );
}
