#!/usr/bin/env python3
"""Instala todo lo que falta para generar documentos, sin decisiones.

Pensado para quien no quiere pensar en versiones, rutas ni dependencias: mira
qué falta, lo instala y avisa en castellano si quedó listo.

Qué hace, en orden:

1. Consulta ``verificar_entorno.py --strict --json`` (sólo lectura) para saber
   qué falta exactamente.
2. Instala los programas del sistema que falten con ``winget``.
3. Instala las librerías de Python con ``pip install -r requirements.txt``.
4. Instala la dependencia de Node con ``npm install``.
5. Vuelve a verificar y resume el resultado.

Nunca instala algo que ya está, nunca usa ``--force`` y nunca toca nada dentro
de ``usuario/``. Si algo falla, se detiene y muestra el error real.

Sólo usa la biblioteca estándar.

Uso::

    python herramientas/scripts/instalar_todo.py --plan   # sólo muestra el plan
    python herramientas/scripts/instalar_todo.py          # pregunta y ejecuta
    python herramientas/scripts/instalar_todo.py --si     # sin preguntar
    python herramientas/scripts/instalar_todo.py --si --sin-ocr

Salida: ``0`` si quedó todo listo, ``1`` si falta algo o si algo falló.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_SCRIPTS = Path(__file__).resolve().parent
VERIFICADOR = DIR_SCRIPTS / "verificar_entorno.py"

# El módulo vive al lado de este script. Al correrlo como script, su carpeta ya
# está en sys.path; al importarlo por ruta (pruebas) hay que agregarla.
if str(DIR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIR_SCRIPTS))

from entorno_windows import refrescar_path  # noqa: E402

# clave del verificador -> (id de winget, nombre para mostrar, para qué sirve)
PROGRAMAS = {
    "git": ("Git.Git", "Git", "guarda versiones del proyecto"),
    "node": ("OpenJS.NodeJS.LTS", "Node.js", "arma los documentos Word"),
    "pandoc": ("JohnMacFarlane.Pandoc", "Pandoc", "lee y convierte documentos"),
    "soffice": (
        "TheDocumentFoundation.LibreOffice",
        "LibreOffice",
        "convierte entre Word, PDF y Excel",
    ),
    "pdftoppm": ("oschwartz10612.Poppler", "Poppler", "revisa cómo quedó un PDF"),
    "tesseract": ("tesseract-ocr.tesseract", "Tesseract", "lee PDF que son una foto"),
}

ORDEN = ("git", "node", "pandoc", "soffice", "pdftoppm", "tesseract")


def leer_estado() -> dict | None:
    """Devuelve el informe del verificador, o None si no se pudo leer."""
    try:
        resultado = subprocess.run(
            [sys.executable, str(VERIFICADOR), "--strict", "--json"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=180,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        return json.loads(resultado.stdout)
    except json.JSONDecodeError:
        return None


def faltantes(estado: dict) -> tuple[list[str], bool, bool, bool]:
    """Devuelve (programas, necesita_pip, necesita_npm, python_malo)."""
    resultados = estado.get("resultados") or {}
    base = resultados.get("base") or {}
    python_malo = not (base.get("python") or {}).get("ok", True)

    de_formato: set[str] = set()
    for entradas in (resultados.get("formatos") or {}).values():
        for compuesta, datos in entradas.items():
            if not datos.get("ok", True):
                de_formato.add(compuesta)

    # Los opcionales no están en requirements.txt: nunca activan pip. Se miran
    # igual para decidir si hay que instalar un binario opcional (Tesseract).
    opcionales: set[str] = set()
    for compuesta, datos in (resultados.get("opcionales") or {}).items():
        if not datos.get("ok", True):
            opcionales.add(compuesta)

    claves_faltantes = de_formato | opcionales

    programas: list[str] = []
    for clave in ORDEN:
        if f"bin:{clave}" in claves_faltantes and clave in PROGRAMAS:
            programas.append(clave)
    # npm viene con Node.js: no es una instalación aparte.
    if "bin:npm" in de_formato and "node" not in programas:
        programas.append("node")

    necesita_pip = any(c.startswith(("mod:", "cmd:")) for c in de_formato)
    necesita_npm = "npm:docx" in de_formato
    return programas, necesita_pip, necesita_npm, python_malo


def ejecutar(comando: list[str]) -> tuple[bool, str]:
    """Ejecuta un comando mostrando poco texto. Devuelve (ok, detalle)."""
    try:
        resultado = subprocess.run(
            comando,
            cwd=RAIZ,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
        )
    except OSError as exc:
        return False, str(exc)
    if resultado.returncode == 0:
        return True, ""
    salida = (resultado.stderr or "").strip() or (resultado.stdout or "").strip()
    cola = "\n".join(salida.splitlines()[-12:])
    return False, cola or f"código de salida {resultado.returncode}"


def nvm_presente() -> bool:
    """Detecta si Node.js lo maneja NVM (nvm-windows o variantes).

    Con NVM, ``C:\\Program Files\\nodejs`` es un enlace al Node activo. Un
    ``winget install`` de Node.js sobrescribe ese enlace y deja dos
    instalaciones compitiendo: exactamente lo que no hay que hacer.
    """
    if sys.platform != "win32":
        return False
    if os.environ.get("NVM_HOME") or os.environ.get("NVM_SYMLINK"):
        return True
    for clave in ("node", "npm"):
        ruta = shutil.which(clave)
        if ruta and "nvm" in ruta.lower():
            return True
    programas = os.environ.get("ProgramFiles")
    if programas:
        enlace = Path(programas) / "nodejs"
        es_junction = getattr(os.path, "isjunction", lambda _: False)
        if enlace.exists() and (enlace.is_symlink() or es_junction(enlace)):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Instala todo lo necesario para generar documentos."
    )
    parser.add_argument("--plan", action="store_true", help="sólo muestra qué haría")
    parser.add_argument("--si", action="store_true", help="no pide confirmación")
    parser.add_argument(
        "--con-ocr",
        action="store_true",
        help="instala además Tesseract, para leer PDF escaneados (opcional)",
    )
    args = parser.parse_args(argv)

    print("=" * 68)
    print("  INSTALADOR DEL ORQUESTADOR DOCUMENTAL")
    print("=" * 68)
    print()

    if sys.platform != "win32":
        print("Este instalador automático es para Windows.")
        print("En Linux o macOS seguí la sección «Linux y macOS» de INSTALACION.md.")
        return 1

    refrescar_path()

    estado = leer_estado()
    if estado is None:
        print("No pude revisar qué falta. Probá de nuevo desde la carpeta del proyecto:")
        print("  python herramientas/scripts/verificar_entorno.py")
        print("Si sigue fallando, pasale este mensaje al agente.")
        return 1

    programas, necesita_pip, necesita_npm, python_malo = faltantes(estado)
    if not args.con_ocr and "tesseract" in programas:
        # OCR es opcional: sin él no se puede leer un PDF escaneado, nada más.
        programas.remove("tesseract")

    protegidos: list[str] = []
    if "node" in programas and nvm_presente():
        # Nunca instalar Node encima de NVM: rompe el enlace al Node activo.
        programas.remove("node")
        protegidos.append(
            "Node.js lo maneja NVM: no lo toco. Si falta, usá «nvm install --lts»."
        )
        if necesita_npm:
            # Sin Node no se puede correr npm: se avisa en vez de fallar más abajo.
            necesita_npm = False
            protegidos.append(
                "La librería de Node no se instala desde acá. Pedile al agente que lo resuelva."
            )

    if python_malo:
        print("El problema no es una dependencia: la versión de Python es vieja.")
        print("Hace falta Python 3.10 o más nuevo.")
        print()
        print("No te pelees con esto: copiá este mensaje y pegáselo al agente.")
        return 1

    tareas: list[str] = []
    for clave in programas:
        _, nombre, para_que = PROGRAMAS[clave]
        tareas.append(f"Instalar {nombre} ({para_que})")
    if necesita_pip:
        tareas.append("Instalar las librerías de Python")
    if necesita_npm:
        tareas.append("Instalar la librería de Node")

    if not tareas:
        print("No falta nada: el entorno ya está listo.")
        print()
        print("TODO LISTO")
        return 0

    print(
        f"Encontré {len(tareas)} {'cosa' if len(tareas) == 1 else 'cosas'} para instalar"
        " en esta computadora:"
    )
    print()
    for numero, tarea in enumerate(tareas, start=1):
        print(f"  {numero}. {tarea}")
    print()
    print("No se toca ningún dato tuyo. Sólo se instalan programas.")
    print()
    if protegidos:
        for aviso in protegidos:
            print(f"  Aviso: {aviso}")
        print()

    if args.plan:
        print("(--plan: no se instaló nada)")
        return 0

    if not args.si:
        try:
            respuesta = input("¿Empezamos? Escribí S y apretá Enter: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if respuesta not in {"s", "si", "sí", "y", "yes"}:
            print("Cancelado. No se instaló nada.")
            return 1
        print()

    if programas and shutil.which("winget") is None:
        print("No encuentro el instalador de Windows (winget).")
        print("Actualizá «Instalador de aplicaciones» desde Microsoft Store,")
        print("o pedile al agente que lo resuelva.")
        return 1

    print("Esto puede tardar varios minutos. No cierres esta ventana.")
    if programas:
        print("Windows te va a pedir permiso para instalar: aceptá.")
    print()

    fallos: list[str] = []

    for numero, clave in enumerate(programas, start=1):
        identificador, nombre, _ = PROGRAMAS[clave]
        print(f"[{numero}/{len(tareas)}] {nombre}...", flush=True)
        ok, detalle = ejecutar(
            [
                "winget",
                "install",
                "--id",
                identificador,
                "--exact",
                "--silent",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        )
        if ok:
            print("      instalado")
            refrescar_path()
        else:
            print("      no se pudo instalar")
            fallos.append(f"{nombre}: {detalle}")

    if necesita_pip:
        print(f"[{len(programas) + 1}/{len(tareas)}] Librerías de Python...", flush=True)
        ok, detalle = ejecutar(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        if ok:
            print("      instaladas")
        else:
            print("      no se pudieron instalar")
            fallos.append(f"Librerías de Python: {detalle}")

    if necesita_npm:
        print(f"[{len(tareas)}/{len(tareas)}] Librería de Node...", flush=True)
        if shutil.which("npm") is None:
            print("      falta Node.js, no se puede continuar con esta parte")
            fallos.append("Librería de Node: npm no está disponible")
        else:
            ok, detalle = ejecutar(["npm", "install", "--no-fund", "--no-audit"])
            if ok:
                print("      instalada")
            else:
                print("      no se pudo instalar")
                fallos.append(f"Librería de Node: {detalle}")

    print()
    print("-" * 68)
    estado_final = leer_estado()
    listos: list[str] = []
    if estado_final:
        formatos = (estado_final.get("resultados") or {}).get("formatos") or {}
        for formato, entradas in formatos.items():
            if all(datos.get("ok") for datos in entradas.values()):
                listos.append(formato)

    if fallos:
        print("FALTAN COSAS. Esto es lo que falló:")
        for detalle in fallos:
            print()
            print(detalle)
        print()
        print("No hace falta que entiendas el error. Copiá todo esto y pegáselo")
        print("al agente con la frase: «esto falló al instalar, arreglalo».")
        return 1

    if listos:
        print(f"Podés crear documentos en: {', '.join(listos)}")
    else:
        print("No pude confirmar los formatos disponibles.")
    print()
    print("TODO LISTO")
    print()
    print("Ahora abrí el agente en esta carpeta y pedile un documento, por ejemplo:")
    print("  «Redactá un memorándum de horarios y guardalo en Word».")
    return 0


if __name__ == "__main__":
    sys.exit(main())
