export interface Producto {
  producto_id: string;
  nombre_modelado: string;
  producto_original: string;
  local_original: string;
  anio: number;
}
export interface Dia {
  fecha: string;
  cantidad: number | null;
}
export interface Ventas {
  producto: Producto;
  diarias: Dia[];
  dias_observados: number;
  dias_sin_fila: number;
  total_observado: number | null;
  incompleta: boolean;
}
export interface Referencia {
  id: string;
  tipo: string;
  fecha_utc: string;
  version_codigo: string;
}
export interface Estado {
  version: string;
  importaciones: { id: string }[];
  ejecuciones: Referencia[];
  regla_ausencias: string;
}
export interface Ingrediente {
  ingrediente_id: string;
  nombre: string;
  unidad: string;
  estado_stock: string;
  control_stock: boolean;
}
export interface Ficha {
  producto_id: string;
  nombre_modelado: string;
  producto_original: string;
  rendimiento_unidades: number;
  adaptacion: string;
  equivalencia_unidad: string;
  fuentes: string[];
  ingredientes: {
    ingrediente_id: string;
    cantidad: number;
    unidad: string;
    componente: string;
  }[];
}
export interface Recetario {
  version: string;
  ingredientes: Ingrediente[];
  recetas: Ficha[];
  fuentes: { fuente_id: string; titulo: string; url: string; autor: string }[];
}
// Las instantáneas históricas conservan el formato de su versión de ejecución.
export interface Registro {
  ejecucion_id: string;
  fecha_utc: string;
  tipo: string;
  contexto: Record<string, any>;
  entradas: Record<string, any>;
  resultado: Record<string, any>;
  huella_contenido: string;
}
export interface Disponibilidad {
  origen: string;
  metodos: Record<
    string,
    {
      completo: boolean;
      faltantes: {
        producto_id: string;
        horizontes: number[];
        causas: string[];
      }[];
    }
  >;
  productos: {
    producto_id: string;
    nombre: string;
    filas: Record<string, any>[];
  }[];
}
export type Metodo = "persistencia" | "semanal" | "random_forest";
export const metodos: Record<Metodo, string> = {
  persistencia: "Última venta registrada",
  semanal: "Referencia semanal",
  random_forest: "Random Forest",
};
export const numero = (n: string | number | null | undefined, max = 2) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("es-AR", { maximumFractionDigits: max }).format(
        Number(n),
      );
export const fechaCorta = (f: string) =>
  f.slice(0, 10).split("-").reverse().slice(0, 2).join("/");
export const fechaCompleta = (f: string) =>
  f.slice(0, 10).split("-").reverse().join("/");
export const prepararSerie = (dias: Dia[]) => dias.map((d) => ({ ...d }));
export function decimalDeEntrada(valor: string): string {
  const texto = valor.trim().replace(",", ".");
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(texto))
    throw new Error(
      "Ingresá una cantidad decimal no negativa, sin separadores de miles.",
    );
  return texto;
}
export const etiquetaResultado = (n: number) =>
  n ? `${n} insumos requieren reposición` : "Sin faltantes en este escenario";
