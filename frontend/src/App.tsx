import { useEffect, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  CalendarRange,
  ChartNoAxesCombined,
  ChevronRight,
  CircleHelp,
  Database,
  History,
  Menu,
  Moon,
  Sun,
  UtensilsCrossed,
  X,
} from "lucide-react";
import { api, parametros, useCarga } from "./api";
import { Aviso, Cargando } from "./componentes";
import type { Estado, Producto, Recetario } from "./modelos";
import Ventas from "./paginas/Ventas";
import Recetas from "./paginas/Recetas";
import Evaluacion from "./paginas/Evaluacion";
import Historial from "./paginas/Historial";
import Planificar from "./paginas/Planificar";
import Respaldo from "./paginas/Respaldo";

const navegacion = [
  { id: "ventas", nombre: "Ventas", icono: ChartNoAxesCombined },
  { id: "pronosticos", nombre: "Pronósticos", icono: Activity },
  { id: "planificar", nombre: "Planificar", icono: CalendarRange },
  { id: "recetas", nombre: "Recetario", icono: BookOpen },
  { id: "evaluacion", nombre: "Evaluación", icono: ChartNoAxesCombined },
  { id: "historial", nombre: "Historial", icono: History },
  { id: "respaldo", nombre: "Datos y copias", icono: Database },
];

export default function App() {
  const [pagina, setPagina] = useState(location.hash.slice(1) || "ventas");
  const [tema, setTema] = useState(
    () =>
      localStorage.getItem("planificacion-tema") ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro"),
  );
  const [abierta, setAbierta] = useState(false);
  const [revision, setRevision] = useState(0);
  const [importacion, setImportacion] = useState("");
  const estado = useCarga(() => api<Estado>("/estado"), [revision], true);
  const recetas = useCarga(() => api<Recetario>("/recetas"), []);
  const productos = useCarga(
    () =>
      importacion
        ? api<Producto[]>("/productos" + parametros({ importacion }))
        : Promise.resolve([]),
    [importacion],
  );
  const alGuardar = () => setRevision((n) => n + 1);
  useEffect(() => {
    document.documentElement.dataset.tema = tema;
    localStorage.setItem("planificacion-tema", tema);
  }, [tema]);
  useEffect(() => {
    if (!importacion && estado.datos?.importaciones.length)
      setImportacion(estado.datos.importaciones.at(-1)!.id);
  }, [estado.datos, importacion]);
  useEffect(() => {
    const cambiar = () => {
      setPagina(location.hash.slice(1) || "ventas");
      setAbierta(false);
      window.scrollTo(0, 0);
    };
    addEventListener("hashchange", cambiar);
    return () => removeEventListener("hashchange", cambiar);
  }, []);
  const seccion = navegacion.find((n) => n.id === pagina) || navegacion[0];
  const listo = estado.datos && recetas.datos && productos.datos;
  return (
    <div className="aplicacion">
      <a
        className="saltar"
        href="#contenido"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("contenido")?.focus();
        }}
      >
        Saltar al contenido
      </a>
      {abierta && (
        <button
          className="fondo-menu"
          onClick={() => setAbierta(false)}
          aria-label="Cerrar navegación"
        />
      )}
      <aside className={`sidebar ${abierta ? "abierta" : ""}`}>
        <a href="#ventas" className="marca">
          <span className="isotipo">
            <UtensilsCrossed size={21} />
          </span>
          <span>
            Planificación<small>COCINA E INVENTARIO</small>
          </span>
        </a>
        <div className="nav-titulo">ESPACIO DE TRABAJO</div>
        <nav aria-label="Secciones">
          {navegacion.map((n) => (
            <a
              key={n.id}
              href={"#" + n.id}
              className={seccion.id === n.id ? "activo" : ""}
              aria-current={seccion.id === n.id ? "page" : undefined}
            >
              <n.icono size={18} />
              {n.nombre}
              {seccion.id === n.id && <span className="punto-activo" />}
            </a>
          ))}
        </nav>
        <div className="sidebar-pie">
          <div className="local-chip">
            <span className="punto-verde" /> Entorno local
          </div>
          <p>
            Ventas observadas.
            <br />
            Recetas modeladas.
            <br />
            Inventario sintético.
          </p>
          <small>Prototipo {estado.datos?.version || ""}</small>
        </div>
      </aside>
      <div className="contenido">
        <header className="barra">
          <div className="migas">
            <button
              className="icono-boton movil"
              aria-label="Abrir navegación"
              onClick={() => setAbierta(!abierta)}
            >
              <Menu size={20} />
            </button>
            <span>Espacio de trabajo</span>
            <ChevronRight size={14} />
            <strong>{seccion.nombre}</strong>
          </div>
          <div className="barra-derecha">
            <span className="estado-conexion">
              <span className="punto-verde" />
              {estado.error ? "Sin conexión" : "Conectado al motor local"}
            </span>
            <button
              className="icono-boton tema"
              title={
                tema === "oscuro"
                  ? "Cambiar a tema claro"
                  : "Cambiar a tema oscuro"
              }
              aria-label={
                tema === "oscuro"
                  ? "Cambiar a tema claro"
                  : "Cambiar a tema oscuro"
              }
              onClick={() => setTema(tema === "oscuro" ? "claro" : "oscuro")}
            >
              {tema === "oscuro" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>
        <main id="contenido" tabIndex={-1}>
          {estado.error || recetas.error || productos.error ? (
            <Aviso tipo="error">
              {estado.error || recetas.error || productos.error}{" "}
              <button className="texto-boton" onClick={alGuardar}>
                Volver a intentar
              </button>
            </Aviso>
          ) : !listo ? (
            <Cargando />
          ) : pagina === "respaldo" ? (
            <Respaldo alGuardar={alGuardar} />
          ) : pagina === "recetas" ? (
            <Recetas datos={recetas.datos!} />
          ) : pagina === "historial" ? (
            <Historial ejecuciones={estado.datos!.ejecuciones} />
          ) : pagina === "evaluacion" ? (
            <Evaluacion ejecuciones={estado.datos!.ejecuciones} />
          ) : !importacion ? (
            <Aviso>
              Primero cargá los originales desde{" "}
              <a href="#respaldo">Datos y copias</a>.
            </Aviso>
          ) : pagina === "planificar" || pagina === "pronosticos" ? (
            <Planificar
              key={pagina + importacion}
              importacion={importacion}
              productos={productos.datos!}
              recetas={recetas.datos!}
              ejecuciones={estado.datos!.ejecuciones}
              alGuardar={alGuardar}
              individual={pagina === "pronosticos"}
            />
          ) : (
            <Ventas
              key={importacion}
              importacion={importacion}
              productos={productos.datos!}
            />
          )}
          <footer>
            <span>Planificación gastronómica · Apoyo a decisiones</span>
            <span>Los resultados corresponden al escenario consultado.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
