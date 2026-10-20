import { useState } from "react";
import { Archive, FolderInput, RotateCcw } from "lucide-react";
import { api } from "../api";
import { Aviso, Cabecera, Campo, Panel } from "../componentes";

export default function Respaldo({ alGuardar }: { alGuardar: () => void }) {
  const [carpeta, setCarpeta] = useState("datos/originales");
  const [destino, setDestino] = useState(
    `respaldos/copia_${new Date().toISOString().replace(/[:.]/g, "-")}.sqlite3`,
  );
  const [copia, setCopia] = useState("");
  const [restaurada, setRestaurada] = useState("datos/restaurada.sqlite3");
  const [ocupado, setOcupado] = useState(false);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  async function ejecutar(ruta: string, cuerpo: unknown, exito: string) {
    setOcupado(true);
    setError("");
    setMensaje("");
    try {
      await api(ruta, cuerpo);
      setMensaje(exito);
      alGuardar();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setOcupado(false);
    }
  }
  return (
    <>
      <Cabecera
        etiqueta="DATOS Y CONSERVACIÓN"
        titulo="El trabajo, a resguardo."
        descripcion="Importá originales comprobados y conservá copias consistentes de tus ejecuciones."
      />
      {error && <Aviso tipo="error">{error}</Aviso>}
      {mensaje && <Aviso tipo="ok">{mensaje}</Aviso>}
      <Panel titulo="Importar ventas" detalle={<FolderInput size={19} />}>
        <p className="prosa">
          Elegí una carpeta local con los originales del manifiesto. El control
          se completa antes de guardar la importación.
        </p>
        <div className="filtros interna">
          <Campo nombre="Carpeta de originales">
            <input
              value={carpeta}
              onChange={(e) => setCarpeta(e.target.value)}
            />
          </Campo>
          <button
            className="boton"
            disabled={ocupado}
            onClick={() =>
              ejecutar(
                "/importaciones",
                { carpeta },
                "Originales comprobados e importación disponible.",
              )
            }
          >
            Validar e importar
          </button>
        </div>
      </Panel>
      <Panel titulo="Crear una copia" detalle={<Archive size={19} />}>
        <div className="filtros interna">
          <Campo nombre="Destino nuevo">
            <input
              value={destino}
              onChange={(e) => setDestino(e.target.value)}
            />
          </Campo>
          <button
            className="boton secundario"
            disabled={ocupado}
            onClick={() =>
              ejecutar(
                "/copias",
                { destino },
                "Copia creada y comprobada. Conservá también su manifiesto JSON.",
              )
            }
          >
            Crear copia
          </button>
        </div>
        <p className="nota">
          El destino debe ser nuevo. Se conserva un manifiesto con la huella de
          la copia.
        </p>
      </Panel>
      <Panel titulo="Restaurar una copia" detalle={<RotateCcw size={19} />}>
        <div className="filtros interna">
          <Campo nombre="Archivo de copia">
            <input value={copia} onChange={(e) => setCopia(e.target.value)} />
          </Campo>
          <Campo nombre="Destino nuevo">
            <input
              value={restaurada}
              onChange={(e) => setRestaurada(e.target.value)}
            />
          </Campo>
          <button
            className="boton secundario"
            disabled={ocupado || !copia}
            onClick={() =>
              ejecutar(
                "/restauraciones",
                { origen: copia, destino: restaurada },
                "Restauración comprobada en el archivo nuevo. La base activa se conserva.",
              )
            }
          >
            Restaurar
          </button>
        </div>
        <p className="nota">
          Para abrir la base restaurada, iniciá el servidor con su ruta mediante
          --base.
        </p>
      </Panel>
    </>
  );
}
