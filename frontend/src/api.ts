import { useEffect, useState } from "react";
import type { DependencyList } from "react";

export async function api<T>(ruta: string, cuerpo?: unknown): Promise<T> {
  const respuesta = await fetch(
    `/api${ruta}`,
    cuerpo === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cuerpo),
        },
  );
  const contenido = await respuesta.json().catch(() => null);
  if (!respuesta.ok)
    throw new Error(
      contenido?.mensaje ||
        `No se pudo completar la consulta (${respuesta.status}).`,
    );
  return contenido as T;
}
export const parametros = (datos: Record<string, string>) =>
  `?${new URLSearchParams(datos)}`;
export function useCarga<T>(
  cargar: () => Promise<T>,
  dependencias: DependencyList,
  conservarDatos = false,
) {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(true);
  useEffect(() => {
    let activa = true;
    setCargando(true);
    setError("");
    if (!conservarDatos) setDatos(null);
    cargar()
      .then((d) => {
        if (activa) setDatos(d);
      })
      .catch((e) => {
        if (activa) setError(e.message);
      })
      .finally(() => {
        if (activa) setCargando(false);
      });
    return () => {
      activa = false;
    };
  }, dependencias);
  return { datos, error, cargando };
}
export function descargarJSON(datos: unknown, nombre: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(datos, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  a.click();
  URL.revokeObjectURL(url);
}
