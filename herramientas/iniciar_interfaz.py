"""Construcción local para repositorios en unidades sincronizadas y servidor React."""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def preparar(raiz: Path, comprobar=False) -> Path:
    frontend = raiz/'frontend'
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Instalá Node.js 22.12 o posterior antes de construir la interfaz.')
    version = subprocess.check_output([node,'--version'],text=True).strip()
    mayor,menor = map(int,re.match(r'v(\d+)\.(\d+)',version).groups())
    if not (mayor==20 and menor>=19 or mayor==22 and menor>=12 or mayor>22):
        raise RuntimeError('Vite requiere Node.js 20.19+, 22.12+ o una versión posterior compatible.')
    npm_cli = Path(node).parent/'node_modules/npm/bin/npm-cli.js'
    if not npm_cli.is_file():
        candidato = Path(shutil.which('npm') or '').resolve()
        if candidato.suffix=='.js':
            npm_cli = candidato
        else:
            raise RuntimeError('No se encontró npm junto a Node.js. Usá una instalación estándar de Node.')
    archivos = []
    for carpeta, directorios, nombres in os.walk(frontend):
        directorios[:] = [d for d in directorios if d not in ('node_modules','dist')]
        archivos.extend(Path(carpeta)/n for n in nombres if not n.endswith('.tsbuildinfo'))
    sha = hashlib.sha256(str(raiz).encode())
    for p in sorted(archivos):
        sha.update(p.relative_to(frontend).as_posix().encode()); sha.update(p.read_bytes())
    trabajo = Path(tempfile.gettempdir())/'tfg_interfaz'/sha.hexdigest()[:20]
    trabajo.mkdir(parents=True,exist_ok=True)
    for p in archivos:
        destino = trabajo/p.relative_to(frontend)
        destino.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,destino)
    def npm(*args):
        subprocess.run([node,str(npm_cli),*args],cwd=trabajo,check=True)
    if not (trabajo/'node_modules').is_dir():
        npm('ci')
    if comprobar:
        npm('test')
    if comprobar or not (trabajo/'dist/index.html').is_file():
        npm('run','build')
    return trabajo/'dist'


def main():
    raiz = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description='Construir y abrir el servidor local de la interfaz React')
    p.add_argument('--comprobar',action='store_true')
    p.add_argument('--solo-construir',action='store_true')
    p.add_argument('--base',type=Path,default=raiz/'datos/prototipo.sqlite3')
    args = p.parse_args()
    cliente = preparar(raiz,args.comprobar)
    print(f'Interfaz comprobada: {cliente}',flush=True)
    if args.solo_construir:
        return
    import uvicorn
    from planificacion.presentacion.api import crear_app
    os.chdir(raiz)
    print('Abrí http://127.0.0.1:8765 — mantené esta ventana abierta.',flush=True)
    uvicorn.run(crear_app(args.base,cliente),host='127.0.0.1',port=8765)


if __name__=='__main__':
    main()
