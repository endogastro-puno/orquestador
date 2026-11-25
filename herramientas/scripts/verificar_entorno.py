#!/usr/bin/env python3
"""Verifica que el entorno tenga lo necesario para generar documentos.

Comprueba dos clases de requisito:

* **Base** — obligatoria siempre: Python 3.10+ y ``git``.
* **Por formato** — cada formato de salida necesita cosas distintas:

  ==========  ==========================================================
  Formato     Requisitos
  ==========  ==========================================================
  ``docx``    Node.js + paquete npm ``docx``, Pandoc, LibreOffice,
              ``defusedxml``, ``lxml``, ``validators``, Pillow
  ``xlsx``    LibreOffice, ``openpyxl``, ``pandas``
  ``pdf``     Poppler (``pdftoppm``), ``pypdf``, ``pdfplumber``,
              ``reportlab``, ``pdf2image``, Pillow
  ``markdown`` nada (escritura directa)
  ==========  ==========================================================

Tesseract y ``pytesseract`` sólo hacen falta para PDF escaneado (OCR), y
``markitdown`` sólo para mirar una hoja de cálculo desde la terminal: los tres
son opcionales.

Sólo lee: no instala, no descarga y no modifica nada. Lo único que cambia es el
``PATH`` de su propio proceso, que relee del registro de Windows para ver los
programas instalados en esta misma sesión.

Sólo usa la biblioteca estándar.

Uso::

    python herramientas/scripts/verificar_entorno.py
    python herramientas/scripts/verificar_entorno.py --formato docx
    python herramientas/scripts/verificar_entorno.py --formato pdf --strict
    python herramientas/scripts/verificar_entorno.py --json

Salida: ``0`` si no falta nada obligatorio, ``1`` si falta algo.

Sin ``--formato`` sólo son obligatorios los requisitos base; los de cada
formato se informan como advertencia. Con ``--formato docx`` los requisitos de
ese formato pasan a ser obligatorios. Con ``--strict`` lo son todos.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_SCRIPTS = Path(__file__).resolve().parent
MINIMO_PYTHON = (3, 10)
TIEMPO_LIMITE = 30

# Módulo compartido con instalar_todo.py. Al correr este archivo como script su
# carpeta ya está en sys.path; al importarlo por ruta hay que agregarla.
if str(DIR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIR_SCRIPTS))

from entorno_windows import refrescar_path  # noqa: E402

# (clave, etiqueta, argumentos para pedir la versión)
BINARIOS = {
    "git": ("git", ["--version"]),
    "node": ("Node.js", ["--version"]),
    "npm": ("npm", ["--version"]),
    "pandoc": ("Pandoc", ["--version"]),
    "soffice": ("LibreOffice (soffice)", ["--version"]),
    "pdftoppm": ("Poppler (pdftoppm)", ["-v"]),
    "tesseract": ("Tesseract OCR", ["--version"]),
}

MODULOS = {
    "docx": "python-docx",
    "PIL": "Pillow",
    "defusedxml": "defusedxml",
    "lxml": "lxml",
    "validators": "validators",
    "openpyxl": "openpyxl",
    "pandas": "pandas",
    "pypdf": "pypdf",
    "pdfplumber": "pdfplumber",
    "reportlab": "reportlab",
    "pdf2image": "pdf2image",
    "pytesseract": "pytesseract",
}

# Requisito: ("bin" | "mod" | "npm" | "cmd", clave)
FORMATOS = {
    "docx": [
        ("bin", "node"),
        ("bin", "npm"),
        ("npm", "docx"),
        ("mod", "docx"),
        ("bin", "pandoc"),
        ("bin", "soffice"),
        ("mod", "defusedxml"),
        ("mod", "lxml"),
        ("mod", "validators"),
        ("mod", "PIL"),
    ],
    "xlsx": [
        ("bin", "soffice"),
        ("mod", "openpyxl"),
        ("mod", "pandas"),
    ],
    "pdf": [
        ("bin", "pdftoppm"),
        ("mod", "pypdf"),
        ("mod", "pdfplumber"),
        ("mod", "reportlab"),
        ("mod", "pdf2image"),
        ("mod", "PIL"),
    ],
    "markdown": [],
}

# Extras que mejoran la calidad de la revisión pero no bloquean.
OPCIONALES = [
    ("bin", "tesseract"),
    ("mod", "pytesseract"),
    ("cmd", "markitdown"),
]

# Cómo se arregla cada faltante.
COMO_INSTALAR = {
    "git": "winget install Git.Git  |  apt install git  |  brew install git",
    "node": "winget install OpenJS.NodeJS.LTS  |  ver INSTALACION.md",
    "npm": "viene con Node.js",
    "docx": "npm install   (en la raíz del repositorio, instala lo de package.json)",
    "pandoc": "winget install JohnMacFarlane.Pandoc",
    "soffice": "winget install TheDocumentFoundation.LibreOffice",
    "pdftoppm": "winget install oschwartz10612.Poppler",
    "tesseract": "winget install tesseract-ocr.tesseract",
    "markitdown": "opcional: pip install markitdown  (vistazo rápido de una hoja)",
}

# Paquetes que NO están en requirements.txt: se instalan a mano si se necesitan.
EXTRA_OPCIONAL = {
    "pytesseract": "opcional: pip install pytesseract  (requiere el binario tesseract)",
}


def _candidatos(nombre: str) -> list[Path]:
    """Rutas de instalación típicas cuando el binario no está en PATH."""
    candidatos: list[Path] = []
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(variable)
        if not base:
            continue
        programa = Path(base)
        if nombre == "soffice":
            candidatos.append(programa / "LibreOffice" / "program" / "soffice.exe")
        elif nombre == "pdftoppm":
            candidatos.append(programa / "poppler" / "Library" / "bin" / "pdftoppm.exe")
    if nombre == "soffice":
        candidatos.append(Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"))
    return candidatos


def version_binario(nombre: str) -> str | None:
    """Devuelve la versión de un binario, o None si no está instalado."""
    etiqueta, argumentos = BINARIOS.get(nombre, (nombre, ["--version"]))
    ruta = shutil.which(nombre)
    if not ruta:
        for candidato in _candidatos(nombre):
            if candidato.is_file():
                ruta = str(candidato)
                break
    if not ruta:
        return None
    if nombre == "soffice":
        # En Windows ``soffice.exe`` es una aplicación de GUI: no escribe en la
        # consola, y el lanzador ``.com`` imprime la versión y después se queda
        # esperando un Enter. Ejecutarlo sólo para leer un número abre ventanas y
        # deja la consola colgada. Saber que está instalado es lo único que hace
        # falta para decidir si el formato se puede generar.
        return "instalado"
    try:
        resultado = subprocess.run(
            [ruta, *argumentos],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=TIEMPO_LIMITE,
        )
    except (OSError, subprocess.SubprocessError):
        return "instalado (versión desconocida)"
    salida = (resultado.stdout or "").strip() or (resultado.stderr or "").strip()
    if not salida:
        return "instalado (versión desconocida)"
    primera = salida.splitlines()[0].strip()
    return primera[:70] or "instalado (versión desconocida)"


def version_modulo(nombre: str) -> str | None:
    """Devuelve la versión de un módulo de Python, o None si no está instalado."""
    try:
        if importlib.util.find_spec(nombre) is None:
            return None
    except (ImportError, ValueError, ModuleNotFoundError):
        return None
    try:
        import importlib.metadata as metadatos
    except ImportError:  # pragma: no cover - Python < 3.8
        return "instalado"
    paquete = MODULOS.get(nombre, nombre)
    for candidato in (paquete, nombre):
        try:
            return metadatos.version(candidato)
        except Exception:
            continue
    return "instalado"


def version_npm(paquete: str) -> str | None:
    """Comprueba si un paquete npm se puede resolver desde el repositorio."""
    if shutil.which("node") is None:
        return None
    try:
        resultado = subprocess.run(
            ["node", "-e", f"console.log(require.resolve('{paquete}'))"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=TIEMPO_LIMITE,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if resultado.returncode == 0 and resultado.stdout.strip():
        return "instalado (local)"
    # Puede estar instalado de forma global: se busca en la raíz de npm global.
    try:
        global_root = subprocess.run(
            ["npm", "root", "-g"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=TIEMPO_LIMITE,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if global_root.returncode != 0:
        return None
    ruta = Path(global_root.stdout.strip()) / paquete / "package.json"
    if ruta.is_file():
        return "instalado (global)"
    return None


def version_comando(nombre: str) -> str | None:
    """Binario que instala pip y expone un ejecutable en PATH."""
    ruta = shutil.which(nombre)
    if ruta:
        return ruta
    if version_modulo(nombre) is not None:
        return f"python -m {nombre}"
    return None


def revisar(tipo: str, clave: str) -> str | None:
    if tipo == "bin":
        return version_binario(clave)
    if tipo == "mod":
        return version_modulo(clave)
    if tipo == "npm":
        return version_npm(clave)
    if tipo == "cmd":
        return version_comando(clave)
    raise ValueError(f"tipo de requisito desconocido: {tipo}")


def etiqueta(tipo: str, clave: str) -> str:
    if tipo == "bin":
        return BINARIOS.get(clave, (clave,))[0]
    if tipo == "mod":
        return MODULOS.get(clave, clave)
    if tipo == "npm":
        return f"paquete npm '{clave}'"
    return f"comando '{clave}'"


def python_ok() -> tuple[bool, str]:
    actual = sys.version_info[:2]
    return actual >= MINIMO_PYTHON, f"{sys.version.split()[0]} (se requiere 3.10+)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verifica el entorno necesario para generar documentos."
    )
    parser.add_argument(
        "--formato",
        choices=(*sorted(FORMATOS), "todos"),
        default="todos",
        help="exige los requisitos de este formato (por defecto: sólo la base)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exige todos los formatos, no sólo el indicado",
    )
    parser.add_argument("--json", action="store_true", help="salida JSON")
    args = parser.parse_args(argv)

    # Un programa instalado hace un minuto no está en el PATH de esta ventana:
    # se relee del registro antes de mirar nada, o el informe mentiría.
    refrescar_path()

    resultados: dict[str, dict[str, object]] = {"base": {}, "formatos": {}, "opcionales": {}}

    # --- Base ---
    ok_python, detalle_python = python_ok()
    resultados["base"]["python"] = {"ok": ok_python, "detalle": detalle_python}
    for clave in ("git",):
        version = version_binario(clave)
        resultados["base"][clave] = {"ok": version is not None, "detalle": version}

    # --- Por formato ---
    for formato, requisitos in FORMATOS.items():
        entradas: dict[str, dict[str, object]] = {}
        for tipo, clave in requisitos:
            version = revisar(tipo, clave)
            entradas[f"{tipo}:{clave}"] = {"ok": version is not None, "detalle": version}
        resultados["formatos"][formato] = entradas

    # --- Opcionales ---
    for tipo, clave in OPCIONALES:
        version = revisar(tipo, clave)
        resultados["opcionales"][f"{tipo}:{clave}"] = {"ok": version is not None, "detalle": version}

    faltantes_obligatorios: list[tuple[str, str]] = []
    faltantes_opcionales: list[tuple[str, str]] = []

    def agregar(destino: list[tuple[str, str]], tipo: str, clave: str) -> None:
        nombre = etiqueta(tipo, clave)
        if tipo == "mod":
            instruccion = EXTRA_OPCIONAL.get(clave) or (
                f"pip install -r requirements.txt  ({MODULOS.get(clave, clave)})"
            )
        elif tipo == "npm":
            instruccion = COMO_INSTALAR.get(clave, f"npm install {clave}")
        else:
            instruccion = COMO_INSTALAR.get(clave, "")
        if any(nombre == existente for existente, _ in destino):
            return
        destino.append((nombre, instruccion))

    for clave, datos in resultados["base"].items():
        if datos["ok"]:
            continue
        nombre = "Python 3.10+" if clave == "python" else BINARIOS.get(clave, (clave,))[0]
        faltantes_obligatorios.append((nombre, COMO_INSTALAR.get(clave, "")))

    for formato, entradas in resultados["formatos"].items():
        for compuesta, datos in entradas.items():
            if datos["ok"]:
                continue
            tipo, clave = compuesta.split(":", 1)
            destino = (
                faltantes_obligatorios
                if (args.strict or formato == args.formato)
                else faltantes_opcionales
            )
            agregar(destino, tipo, clave)

    for compuesta, datos in resultados["opcionales"].items():
        if datos["ok"]:
            continue
        tipo, clave = compuesta.split(":", 1)
        agregar(faltantes_opcionales, tipo, clave)

    if args.json:
        print(
            json.dumps(
                {
                    "python": sys.version.split()[0],
                    "formato_exigido": args.formato,
                    "strict": args.strict,
                    "resultados": resultados,
                    "faltantes_obligatorios": [nombre for nombre, _ in faltantes_obligatorios],
                    "faltantes_opcionales": [nombre for nombre, _ in faltantes_opcionales],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if faltantes_obligatorios else 0

    print("Entorno para el orquestador documental")
    print(f"Repositorio: {RAIZ}")
    print(f"Python:      {sys.version.split()[0]} en {sys.executable}\n")

    print("Base (obligatoria siempre):")
    for clave, datos in resultados["base"].items():
        marca = "[OK]   " if datos["ok"] else "[FALTA]"
        nombre = "Python 3.10+" if clave == "python" else BINARIOS.get(clave, (clave,))[0]
        print(f"  {marca} {nombre:<24} {datos['detalle'] or ''}")

    print("\nPor formato:")
    for formato, entradas in resultados["formatos"].items():
        if not entradas:
            print(f"  .{formato}: no necesita dependencias externas")
            continue
        listos = sum(1 for datos in entradas.values() if datos["ok"])
        estado = "listo" if listos == len(entradas) else f"faltan {len(entradas) - listos}"
        print(f"  .{formato} — {estado}")
        for compuesta, datos in entradas.items():
            marca = "[OK]   " if datos["ok"] else "[FALTA]"
            tipo, clave = compuesta.split(":", 1)
            print(f"    {marca} {etiqueta(tipo, clave):<28} {datos['detalle'] or ''}")

    imprimir_opcionales = any(not datos["ok"] for datos in resultados["opcionales"].values())
    if imprimir_opcionales:
        print("\nOpcionales (no bloquean nada):")
        for compuesta, datos in resultados["opcionales"].items():
            marca = "[OK]   " if datos["ok"] else "[FALTA]"
            tipo, clave = compuesta.split(":", 1)
            print(f"  {marca} {etiqueta(tipo, clave):<28} {datos['detalle'] or ''}")

    if faltantes_obligatorios:
        print(f"\nFaltan {len(faltantes_obligatorios)} requisito(s) obligatorio(s):")
        for nombre, instruccion in faltantes_obligatorios:
            print(f"  - {nombre}")
            if instruccion:
                print(f"      {instruccion}")

    if faltantes_opcionales:
        print(
            f"\nRequisitos de formato ausentes ({len(faltantes_opcionales)}): "
            "no bloquean la base, pero sin ellos ese formato no se puede generar."
        )
        for nombre, instruccion in faltantes_opcionales:
            print(f"  - {nombre}")
            if instruccion:
                print(f"      {instruccion}")

    print("\nGuía completa: INSTALACION.md")
    if faltantes_obligatorios:
        print("Resultado: ENTORNO INCOMPLETO — instalá lo que falta antes de generar.")
        return 1

    listos = [
        formato
        for formato, entradas in resultados["formatos"].items()
        if all(datos["ok"] for datos in entradas.values())
    ]
    pendientes = [formato for formato in resultados["formatos"] if formato not in listos]
    print(f"Formatos listos: {', '.join(listos) if listos else 'ninguno'}")
    if pendientes:
        print(f"Formatos incompletos: {', '.join(pendientes)}")
        print("Resultado: base lista — podés generar lo que esté en 'Formatos listos'.")
        return 0
    print("Resultado: entorno listo para todos los formatos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
