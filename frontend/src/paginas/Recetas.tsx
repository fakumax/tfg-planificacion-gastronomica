import { useState } from "react";
import { BookOpen } from "lucide-react";
import { Cabecera, Campo, Enlace, Panel, Tabla } from "../componentes";
import { numero } from "../modelos";
import type { Recetario } from "../modelos";

export default function Recetas({ datos }: { datos: Recetario }) {
  const [pid, setPid] = useState(datos.recetas[0].producto_id);
  const ficha = datos.recetas.find((r) => r.producto_id === pid)!;
  const insumos = Object.fromEntries(
    datos.ingredientes.map((i) => [i.ingrediente_id, i]),
  );
  return (
    <>
      <Cabecera
        etiqueta="RECETARIO"
        titulo="Del plato al ingrediente."
        descripcion="Fichas modeladas para convertir cantidades previstas en necesidades de insumos."
      />
      <div className="filtros">
        <Campo nombre="Ficha">
          <select value={pid} onChange={(e) => setPid(e.target.value)}>
            {datos.recetas.map((r) => (
              <option key={r.producto_id} value={r.producto_id}>
                {r.producto_id} · {r.nombre_modelado}
              </option>
            ))}
          </select>
        </Campo>
        <span className="etiqueta verde">
          <BookOpen size={14} /> Versión {datos.version}
        </span>
      </div>
      <Panel
        titulo={ficha.nombre_modelado}
        detalle={
          <span className="etiqueta">
            Rinde {ficha.rendimiento_unidades} unidad
          </span>
        }
      >
        <Tabla
          filas={ficha.ingredientes}
          columnas={[
            {
              id: "ingrediente_id",
              titulo: "Ingrediente",
              mostrar: (r) => insumos[r.ingrediente_id].nombre,
            },
            {
              id: "componente",
              titulo: "Componente",
              mostrar: (r) => r.componente.replaceAll("_", " "),
            },
            {
              id: "cantidad",
              titulo: "Cantidad",
              numero: true,
              mostrar: (r) => `${numero(r.cantidad)} ${r.unidad}`,
            },
            {
              id: "estado",
              titulo: "Estado utilizable",
              mostrar: (r) => insumos[r.ingrediente_id].estado_stock,
            },
          ]}
        />
      </Panel>
      <div className="dos-columnas">
        <Panel titulo="Composición del escenario">
          <p className="prosa">{ficha.adaptacion}</p>
          <p className="nota">{ficha.equivalencia_unidad}</p>
        </Panel>
        <Panel titulo="Referencias de composición">
          {datos.fuentes
            .filter((f) => ficha.fuentes.includes(f.fuente_id))
            .map((f) => (
              <div className="referencia" key={f.fuente_id}>
                <Enlace href={f.url}>{f.titulo}</Enlace>
                <small>{f.autor}</small>
              </div>
            ))}
          {!ficha.fuentes.length && (
            <p className="prosa">
              Composición definida para el escenario modelado.
            </p>
          )}
          <p className="nota">
            Las fichas no describen recetas comprobadas del establecimiento.
          </p>
        </Panel>
      </div>
    </>
  );
}
