import { ArrowUpRight, Info, LoaderCircle, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { fechaCorta, fechaCompleta, numero } from "./modelos";
export function Aviso({
  children,
  tipo = "info",
}: {
  children: ReactNode;
  tipo?: "info" | "error" | "stock" | "ok";
}) {
  return (
    <div
      className={`aviso ${tipo}`}
      role={tipo === "error" ? "alert" : "status"}
    >
      {tipo === "error" || tipo === "stock" ? (
        <TriangleAlert size={18} />
      ) : (
        <Info size={18} />
      )}
      <div>{children}</div>
    </div>
  );
}
export function Cargando({
  texto = "Consultando los registros…",
}: {
  texto?: string;
}) {
  return (
    <div className="cargando" role="status">
      <LoaderCircle className="girar" size={20} />
      {texto}
    </div>
  );
}
export function Cabecera({
  etiqueta,
  titulo,
  descripcion,
  children,
}: {
  etiqueta: string;
  titulo: string;
  descripcion: string;
  children?: ReactNode;
}) {
  return (
    <header className="cabecera">
      <div>
        <div className="sobretitulo">{etiqueta}</div>
        <h1>{titulo}</h1>
        <p>{descripcion}</p>
      </div>
      {children && <div className="acciones">{children}</div>}
    </header>
  );
}
export function Campo({
  nombre,
  children,
}: {
  nombre: string;
  children: ReactNode;
}) {
  return (
    <label className="campo">
      <span>{nombre}</span>
      {children}
    </label>
  );
}
export function Panel({
  titulo,
  detalle,
  children,
  className = "",
}: {
  titulo?: string;
  detalle?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {titulo && (
        <div className="panel-titulo">
          <h2>{titulo}</h2>
          {detalle}
        </div>
      )}
      {children}
    </section>
  );
}
export function Tabla({
  columnas,
  filas,
  vacio = "No hay registros para esta consulta.",
}: {
  columnas: {
    id: string;
    titulo: string;
    numero?: boolean;
    mostrar?: (r: any) => ReactNode;
  }[];
  filas: any[];
  vacio?: string;
}) {
  return (
    <div className="tabla-scroll">
      <table>
        <thead>
          <tr>
            {columnas.map((c) => (
              <th key={c.id} className={c.numero ? "numerica" : ""}>
                {c.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((r, n) => (
            <tr key={n}>
              {columnas.map((c) => (
                <td key={c.id} className={c.numero ? "numerica" : ""}>
                  {c.mostrar ? c.mostrar(r) : (r[c.id] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!filas.length && <div className="vacio">{vacio}</div>}
    </div>
  );
}
export function Grafico({
  datos,
  series = [
    {
      clave: "cantidad",
      nombre: "Unidades registradas",
      color: "var(--acento)",
    },
  ],
}: {
  datos: any[];
  series?: { clave: string; nombre: string; color: string }[];
}) {
  return (
    <div
      className="grafico"
      role="img"
      aria-label="Evolución por fecha; los huecos conservan los días sin registro"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={datos}
          margin={{ left: -16, right: 14, top: 12, bottom: 0 }}
        >
          <CartesianGrid
            vertical={false}
            stroke="var(--linea)"
            strokeDasharray="3 4"
          />
          <XAxis
            dataKey="fecha"
            tickFormatter={fechaCorta}
            minTickGap={32}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "var(--suave)", fontSize: 12 }}
            dy={12}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
            tick={{ fill: "var(--suave)", fontSize: 12 }}
          />
          <Tooltip
            labelFormatter={(v) => fechaCompleta(String(v))}
            formatter={(v: any) => numero(v)}
            contentStyle={{
              background: "var(--panel)",
              border: "1px solid var(--linea)",
              borderRadius: 8,
              color: "var(--texto)",
            }}
          />
          {series.length > 1 && <Legend />}
          {series.map((s) => (
            <Line
              key={s.clave}
              dataKey={s.clave}
              name={s.nombre}
              stroke={s.color}
              strokeWidth={2.3}
              type="linear"
              connectNulls={false}
              dot={{ r: 2, strokeWidth: 0, fill: s.color }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
export function Dato({
  etiqueta,
  valor,
  detalle,
}: {
  etiqueta: string;
  valor: ReactNode;
  detalle: string;
}) {
  return (
    <div className="dato">
      <span>{etiqueta}</span>
      <strong>{valor}</strong>
      <small>{detalle}</small>
    </div>
  );
}
export function Enlace({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="enlace">
      {children}
      <ArrowUpRight size={14} />
    </a>
  );
}
