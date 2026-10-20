import { describe, expect, it } from "vitest";
import { decimalDeEntrada, prepararSerie, etiquetaResultado } from "./modelos";

describe("presentación de datos del prototipo", () => {
  it("mantiene un hueco y un cero observado como valores diferentes", () => {
    const r = prepararSerie([
      { fecha: "2025-01-01", cantidad: 0 },
      { fecha: "2025-01-02", cantidad: null },
    ]);
    expect(r.map((d) => d.cantidad)).toEqual([0, null]);
    expect(r.map((d) => d.fecha)).toEqual(["2025-01-01", "2025-01-02"]);
  });
  it("transporta un decimal de mucha precisión sin pasarlo a Number", () => {
    expect(decimalDeEntrada("1109,99999999999999")).toBe("1109.99999999999999");
    expect(decimalDeEntrada("1E-14")).toBe("1E-14");
    expect(() => decimalDeEntrada("")).toThrow();
    expect(() => decimalDeEntrada("-1")).toThrow();
    expect(() => decimalDeEntrada("NaN")).toThrow();
  });
  it("distingue una alerta de stock del fallo de una consulta", () => {
    expect(etiquetaResultado(37)).toBe("37 insumos requieren reposición");
    expect(etiquetaResultado(0)).toBe("Sin faltantes en este escenario");
  });
});
