import { useEffect, useState } from "react";
import { ArrowRight, Check, Plus, Search, Trash2 } from "lucide-react";
import { api, parametros, useCarga } from "../api";
import { Aviso, Cabecera, Campo, Cargando, Panel, Tabla } from "../componentes";
import { decimalDeEntrada, metodos } from "../modelos";
import type {
  Disponibilidad,
  Metodo,
  Producto,
  Recetario,
  Referencia,
  Registro,
} from "../modelos";
import Resultado from "./Resultado";

interface Reposicion {
  entrada_id: string;
  insumo_id: string;
  fecha: string;
  cantidad: string;
  unidad: string;
}
interface Props {
  importacion: string;
  productos: Producto[];
  recetas: Recetario;
  ejecuciones: Referencia[];
  alGuardar: () => void;
  individual?: boolean;
}

export default function Planificar({
  importacion,
  productos,
  recetas,
  ejecuciones,
  alGuardar,
  individual = false,
}: Props) {
  const [origen, setOrigen] = useState(`${productos[0]?.anio || 2025}-11-13`);
  const [metodo, setMetodo] = useState<Metodo>("random_forest");
  const [producto, setProducto] = useState(productos[0]?.producto_id || "P01");
  const selecciones = ejecuciones.filter((e) => e.tipo === "seleccion_modelos");
  const [seleccion, setSeleccion] = useState(selecciones.at(-1)?.id || "");
  const [previa, setPrevia] = useState("");
  const [nombre, setNombre] = useState("Semana de preparación");
  const [version, setVersion] = useState("1");
  const controlados = recetas.ingredientes.filter((i) => i.control_stock);
  const stockInicial = () =>
    Object.fromEntries(controlados.map((i) => [i.ingrediente_id, "0"]));
  const [stock, setStock] = useState<Record<string, string>>(stockInicial);
  const [entradas, setEntradas] = useState<Reposicion[]>([]);
  const [buscar, setBuscar] = useState("");
  const [disponibilidad, setDisponibilidad] = useState<Disponibilidad | null>(
    null,
  );
  const [comprobando, setComprobando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const [resultado, setResultado] = useState<Registro | null>(null);
  const antecedente = useCarga(
    () =>
      previa ? api<Registro>(`/ejecuciones/${previa}`) : Promise.resolve(null),
    [previa],
  );
  useEffect(() => {
    setDisponibilidad(null);
  }, [origen, importacion]);
  useEffect(() => {
    const r = antecedente.datos;
    if (!r) return;
    const e = r.entradas.escenario;
    setOrigen(r.contexto.origen);
    setNombre(e.nombre);
    setVersion(`${e.version}.1`);
    setMetodo(r.contexto.metodo);
    setSeleccion(r.contexto.seleccion_modelos?.seleccion_id || "");
    setStock(
      Object.fromEntries(
        e.existencias.map((e: any) => [e.insumo_id, e.cantidad]),
      ),
    );
    setEntradas(
      e.entradas.map((e: any, n: number) => ({
        ...e,
        entrada_id: e.entrada_id || `legado-${n + 1}`,
      })),
    );
  }, [antecedente.datos]);
  async function comprobar() {
    setComprobando(true);
    setError("");
    setDisponibilidad(null);
    try {
      setDisponibilidad(
        await api<Disponibilidad>(
          "/disponibilidad" + parametros({ importacion, origen }),
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setComprobando(false);
    }
  }
  async function guardar() {
    setOcupado(true);
    setError("");
    setResultado(null);
    try {
      const comun = {
        importacion,
        origen,
        metodo,
        seleccion_id: metodo === "random_forest" ? seleccion || null : null,
      };
      const cuerpo = individual
        ? { ...comun, producto }
        : {
            ...comun,
            nombre,
            version,
            existencias: controlados.map((i) => ({
              insumo_id: i.ingrediente_id,
              unidad: i.unidad,
              cantidad: decimalDeEntrada(stock[i.ingrediente_id]),
            })),
            entradas: entradas.map((e) => ({
              ...e,
              cantidad: decimalDeEntrada(e.cantidad),
            })),
            ejecucion_previa_id: previa || null,
          };
      const registro = await api<Registro>(
        individual ? "/pronosticos" : "/planes",
        cuerpo,
      );
      setResultado(registro);
      alGuardar();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setOcupado(false);
    }
  }
  function agregarEntrada() {
    const f = new Date(origen + "T12:00:00Z");
    f.setUTCDate(f.getUTCDate() + 1);
    setEntradas([
      ...entradas,
      {
        entrada_id: crypto.randomUUID(),
        insumo_id: controlados[0].ingrediente_id,
        unidad: controlados[0].unidad,
        fecha: f.toISOString().slice(0, 10),
        cantidad: "",
      },
    ]);
  }
  function cambiarEntrada(n: number, campo: string, valor: string) {
    setEntradas(
      entradas.map((e, i) =>
        i === n
          ? {
              ...e,
              [campo]: valor,
              ...(campo === "insumo_id"
                ? {
                    unidad: controlados.find((j) => j.ingrediente_id === valor)!
                      .unidad,
                  }
                : {}),
            }
          : e,
      ),
    );
  }
  const disponibilidadActual =
    disponibilidad?.origen === origen ? disponibilidad : null;
  const disponibilidadMetodo = disponibilidadActual?.metodos[metodo];
  const filtrados = controlados.filter((i) =>
    `${i.nombre} ${i.ingrediente_id}`
      .toLowerCase()
      .includes(buscar.toLowerCase()),
  );
  return (
    <>
      <Cabecera
        etiqueta={individual ? "PRONÓSTICOS" : "PLANIFICACIÓN"}
        titulo={
          individual
            ? "Mirar la próxima semana."
            : "Una semana, ingrediente por ingrediente."
        }
        descripcion={
          individual
            ? "Consultá un producto sin exigir que el resto pueda completar un plan."
            : "Definí un escenario de existencias y entradas. El motor calcula consumo, saldos y reposiciones."
        }
      />
      {!individual && (
        <div className="filtros">
          <Campo nombre="Escenario de partida">
            <select
              value={previa}
              onChange={(e) => {
                setPrevia(e.target.value);
                setResultado(null);
                if (!e.target.value) {
                  setStock(stockInicial());
                  setEntradas([]);
                  setNombre("Semana de preparación");
                  setVersion("1");
                }
              }}
            >
              <option value="">Crear un escenario nuevo</option>
              {[...ejecuciones]
                .reverse()
                .filter((e) => e.tipo === "planificacion")
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    Revisar {new Date(e.fecha_utc).toLocaleString("es-AR")} ·{" "}
                    {e.id.slice(0, 8)}
                  </option>
                ))}
            </select>
          </Campo>
        </div>
      )}
      {antecedente.error && <Aviso tipo="error">{antecedente.error}</Aviso>}
      <Panel titulo="01 / Período y método">
        <div className="filtros interna">
          <Campo nombre="Origen · cierre del día">
            <input
              type="date"
              onInput={(e) => setOrigen(e.currentTarget.value)}
              value={origen}
              disabled={!!previa}
              onChange={(e) => setOrigen(e.target.value)}
            />
          </Campo>
          <Campo nombre="Método">
            <select
              value={metodo}
              onChange={(e) => setMetodo(e.target.value as Metodo)}
            >
              {Object.entries(metodos).map(([id, nombre]) => (
                <option key={id} value={id}>
                  {nombre}
                </option>
              ))}
            </select>
          </Campo>
          {individual && (
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
          )}
          {metodo === "random_forest" && (
            <Campo nombre="Selección de configuración">
              <select
                value={seleccion}
                onChange={(e) => setSeleccion(e.target.value)}
              >
                <option value="">Elegir selección cerrada</option>
                {[...selecciones].reverse().map((e) => (
                  <option key={e.id} value={e.id}>
                    {new Date(e.fecha_utc).toLocaleDateString("es-AR")} ·{" "}
                    {e.id.slice(0, 10)}
                  </option>
                ))}
              </select>
            </Campo>
          )}
          <button
            className="boton secundario"
            disabled={comprobando || ocupado || !origen}
            onClick={comprobar}
          >
            {comprobando ? "Comprobando…" : "Comprobar disponibilidad"}
          </button>
        </div>
        {disponibilidadActual && (
          <>
            <Aviso tipo={disponibilidadMetodo?.completo ? "ok" : "info"}>
              {disponibilidadMetodo?.completo ? (
                <>
                  <Check size={14} /> Hay datos para los siete productos y sus
                  siete horizontes.
                </>
              ) : (
                <>
                  El plan completo tiene productos sin entradas suficientes. No
                  es una falla de cálculo.
                </>
              )}
            </Aviso>
            {!individual && !!disponibilidadMetodo?.faltantes.length && (
              <Tabla
                filas={disponibilidadMetodo.faltantes}
                columnas={[
                  { id: "producto_id", titulo: "Producto" },
                  {
                    id: "horizontes",
                    titulo: "Horizontes",
                    mostrar: (r) => r.horizontes.join(", "),
                  },
                  {
                    id: "causas",
                    titulo: "Qué falta",
                    mostrar: (r) => r.causas.join(" · "),
                  },
                ]}
              />
            )}
            <p className="nota">
              Random Forest requiere además una selección compatible. La
              consulta conserva el criterio vigente de ausencias del TP3.
            </p>
          </>
        )}
      </Panel>
      {!individual && (
        <>
          <Panel
            titulo="02 / Existencias iniciales"
            detalle={
              <span className="etiqueta ambar">Escenario sintético</span>
            }
          >
            <div className="filtros interna">
              <Campo nombre="Nombre del escenario">
                <input
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                />
              </Campo>
              <Campo nombre="Versión">
                <input
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                />
              </Campo>
              <div className="buscador">
                <Search size={16} />
                <input
                  aria-label="Buscar insumo"
                  placeholder="Buscar ingrediente"
                  value={buscar}
                  onChange={(e) => setBuscar(e.target.value)}
                />
              </div>
            </div>
            <div className="tabla-scroll stock-tabla">
              <table>
                <thead>
                  <tr>
                    <th>Ingrediente</th>
                    <th>Estado utilizable</th>
                    <th className="numerica">Existencia</th>
                    <th>Unidad</th>
                  </tr>
                </thead>
                <tbody>
                  {filtrados.map((i) => (
                    <tr key={i.ingrediente_id}>
                      <td>{i.nombre}</td>
                      <td className="suave">{i.estado_stock}</td>
                      <td>
                        <input
                          aria-label={`Existencia de ${i.nombre}`}
                          className="cantidad-input"
                          inputMode="decimal"
                          value={stock[i.ingrediente_id] || ""}
                          onChange={(e) =>
                            setStock({
                              ...stock,
                              [i.ingrediente_id]: e.target.value,
                            })
                          }
                        />
                      </td>
                      <td className="suave">{i.unidad}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="nota">
              Ingresá cantidades utilizables, sin separadores de miles. Un stock
              inicial de cero puede producir avisos de reposición; eso es un
              resultado del escenario.
            </p>
          </Panel>
          <Panel
            titulo="03 / Entradas previstas"
            detalle={
              <button className="texto-boton" onClick={agregarEntrada}>
                <Plus size={16} /> Agregar entrega
              </button>
            }
          >
            {!entradas.length ? (
              <div className="vacio">
                Todavía no agregaste entradas. Podés calcular un escenario sin
                reposiciones.
              </div>
            ) : (
              <div className="reposiciones">
                {entradas.map((e, n) => (
                  <div className="reposicion" key={e.entrada_id}>
                    <Campo nombre="Ingrediente">
                      <select
                        value={e.insumo_id}
                        onChange={(ev) =>
                          cambiarEntrada(n, "insumo_id", ev.target.value)
                        }
                      >
                        {controlados.map((i) => (
                          <option
                            key={i.ingrediente_id}
                            value={i.ingrediente_id}
                          >
                            {i.nombre}
                          </option>
                        ))}
                      </select>
                    </Campo>
                    <Campo nombre="Fecha">
                      <input
                        type="date"
                        onInput={(ev) =>
                          cambiarEntrada(n, "fecha", ev.currentTarget.value)
                        }
                        value={e.fecha}
                        onChange={(ev) =>
                          cambiarEntrada(n, "fecha", ev.target.value)
                        }
                      />
                    </Campo>
                    <Campo nombre={`Cantidad (${e.unidad})`}>
                      <input
                        inputMode="decimal"
                        value={e.cantidad}
                        onChange={(ev) =>
                          cambiarEntrada(n, "cantidad", ev.target.value)
                        }
                      />
                    </Campo>
                    <button
                      className="icono-boton"
                      aria-label={`Quitar entrega ${n + 1}`}
                      onClick={() =>
                        setEntradas(entradas.filter((_, i) => i !== n))
                      }
                    >
                      <Trash2 size={17} />
                    </button>
                    <small className="id-entrega">ID {e.entrada_id}</small>
                  </div>
                ))}
              </div>
            )}
            <p className="nota">
              Las entradas se suman antes del consumo del mismo día. Una entrada
              posterior conserva el faltante previo.
            </p>
          </Panel>
        </>
      )}
      {error && <Aviso tipo="error">{error}</Aviso>}
      <div className="guardar-barra">
        <p>
          {individual
            ? "Se guardará una consulta identificada."
            : "Se guardará una nueva ejecución. El escenario anterior se conserva."}
        </p>
        <button
          className="boton"
          onClick={guardar}
          disabled={
            ocupado ||
            comprobando ||
            (!individual && !disponibilidadMetodo?.completo) ||
            (metodo === "random_forest" && !seleccion)
          }
        >
          {ocupado
            ? "Calculando…"
            : individual
              ? "Consultar y guardar"
              : "Calcular y guardar"}
          <ArrowRight size={16} />
        </button>
      </div>
      {ocupado && (
        <Cargando texto="Calculando con información conocida hasta el origen. Puede tardar unos segundos…" />
      )}
      {resultado && (
        <Resultado key={resultado.ejecucion_id} registro={resultado} />
      )}
    </>
  );
}
