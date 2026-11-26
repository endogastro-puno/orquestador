#!/usr/bin/env python3
"""Menú de las facilidades del orquestador.

Un usuario que instala el repo no debería tener que memorizar los comandos
para gozar de las herramientas: este menú los lista, pide lo mínimo que falta
y los corre, pasando su código de salida tal cual.

Uso interactivo::

    python herramientas/scripts/menu.py

Uso directo (sin menú)::

    python herramientas/scripts/menu.py --opcion 4
    python herramientas/scripts/menu.py --opcion 5 -- entrada.docx --json
    python herramientas/scripts/menu.py --opcion 4 --workspace D:\\clientes\\clinica-a

Todo lo que corre el menú es otro script del repositorio: el menú no duplica
lógica, sólo la muestra. No escribe nada por sí mismo.

Códigos de salida: el del script que se corrió (``0`` bien, ``1`` error,
``2`` leído sin texto), o ``1`` si la opción no existe.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DIR_SCRIPTS = Path(__file__).resolve().parent
RAIZ = DIR_SCRIPTS.parents[1]

sys.path.insert(0, str(DIR_SCRIPTS))
import plantillas as pl  # noqa: E402
import workspace as ws  # noqa: E402

DIR_SPECS = RAIZ / "herramientas" / "contratos" / "tipos"

# Cada acción corre OTRO script del repositorio. `workspace` dice si el script
# acepta --workspace; `pide` es la función que junta los argumentos que faltan
# (sólo se usa en modo interactivo).
ACCIONES: list[dict] = [
    {
        "numero": 1,
        "etiqueta": "Ver qué me falta instalar",
        "script": "verificar_entorno.py",
        "workspace": False,
        "pide": None,
    },
    {
        "numero": 2,
        "etiqueta": "Instalar lo que falte (Python, Pandoc, LibreOffice...)",
        "script": "instalar_todo.py",
        "workspace": False,
        "pide": None,
    },
    {
        "numero": 3,
        "etiqueta": "Preparar mi carpeta de datos (crea lo que falta, nunca pisa)",
        "script": "init_local.py",
        "workspace": True,
        "pide": None,
    },
    {
        "numero": 4,
        "etiqueta": "Validar mis datos",
        "script": "validar_datos.py",
        "workspace": True,
        "pide": None,
    },
    {
        "numero": 5,
        "etiqueta": "Leer un documento (Word/Excel, también .doc y .xls viejos; PDF, texto, imagen)",
        "script": "leer_documento.py",
        "workspace": False,
        "pide": "pide_ruta",
    },
    {
        "numero": 6,
        "etiqueta": "Instalar una plantilla que ya tengo",
        "script": "instalar_plantilla.py",
        "workspace": True,
        "pide": "pide_plantilla",
    },
    {
        "numero": 7,
        "etiqueta": "Crear una plantilla inicial",
        "script": "nueva_plantilla.py",
        "workspace": True,
        "pide": "pide_nueva",
    },
    {
        "numero": 8,
        "etiqueta": "Generar un documento (manual, plan operativo)",
        "script": "generar_documento.py",
        "workspace": True,
        "pide": "pide_tipo_declarativo",
    },
    {
        "numero": 9,
        "etiqueta": "Ver mis generadores propios",
        "script": "listar_generadores.py",
        "workspace": True,
        "pide": None,
    },
    {
        "numero": 10,
        "etiqueta": "Verificar que nada mío quedó versionado en git",
        "script": "verificar_limites.py",
        "workspace": True,
        "pide": None,
    },
    {
        "numero": 11,
        "etiqueta": "Prueba de humo del motor",
        "script": "selftest.py",
        "workspace": False,
        "pide": None,
    },
    {
        "numero": 12,
        "etiqueta": "Indexar una carpeta (mapa de mis documentos)",
        "script": "indexar_documentos.py",
        "workspace": True,
        "pide": "pide_carpeta",
    },
    {
        "numero": 13,
        "etiqueta": "Buscar en mis documentos indexados",
        "script": "buscar_documentos.py",
        "workspace": True,
        "pide": "pide_busqueda",
    },
    {
        "numero": 14,
        "etiqueta": "Leer un escaneado con OCR (PDF o foto)",
        "script": "ocr_documento.py",
        "workspace": True,
        "pide": "pide_ocr",
    },
]

PIDE = {}  # se llena abajo con los nombres declarados en ACCIONES


def tipos_declarativos() -> list[str]:
    """Tipos generables: los specs que existen, descubiertos (no duplicados)."""
    return sorted(espec.stem for espec in DIR_SPECS.glob("*.json"))


def registrar(nombre: str):
    def decorador(funcion):
        PIDE[nombre] = funcion
        return funcion

    return decorador


@registrar("pide_ruta")
def pide_ruta() -> list[str]:
    ruta = input("Ruta del archivo a leer (arrastralo acá o pegá la ruta): ").strip().strip('"')
    if not ruta:
        raise ValueError("hace falta la ruta del archivo")
    return [ruta]


@registrar("pide_plantilla")
def pide_plantilla() -> list[str]:
    print(f"Tipos válidos: {', '.join(sorted(pl.TIPOS))}")
    origen = input("Ruta de TU plantilla (la que ya tenés): ").strip().strip('"')
    tipo = input("Tipo de documento: ").strip()
    variante = input("Variante (Enter = base): ").strip() or "base"
    if not origen or not tipo:
        raise ValueError("hacen falta la ruta y el tipo")
    return ["--origen", origen, "--tipo", tipo, "--variante", variante]


@registrar("pide_nueva")
def pide_nueva() -> list[str]:
    print(f"Tipos válidos: {', '.join(sorted(pl.TIPOS))}")
    tipo = input("Tipo de documento: ").strip()
    if not tipo:
        raise ValueError("hace falta el tipo")
    variante = input("Variante (Enter = base): ").strip() or "base"
    formato = input(f"Formato (Enter = {pl.extensiones_de(tipo)[0]}): ").strip()
    argumentos = ["--tipo", tipo, "--variante", variante]
    if formato:
        argumentos += ["--formato", formato]
    return argumentos


@registrar("pide_tipo_declarativo")
def pide_tipo_declarativo() -> list[str]:
    disponibles = tipos_declarativos()
    if not disponibles:
        raise ValueError("no hay specs declarativos instalados")
    print(f"Tipos generables: {', '.join(disponibles)}")
    tipo = input("Tipo a generar: ").strip()
    if not tipo:
        raise ValueError("hace falta el tipo")
    return ["--tipo", tipo]


@registrar("pide_carpeta")
def pide_carpeta() -> list[str]:
    ruta = input("Carpeta a mapear (ej: D:\\FOLDER-PRINCIPAL): ").strip().strip('"')
    if not ruta:
        raise ValueError("hace falta la carpeta")
    return ["--ruta", ruta]


@registrar("pide_busqueda")
def pide_busqueda() -> list[str]:
    consulta = input("Qué buscás (Enter = listar con filtros): ").strip()
    return [consulta] if consulta else []


@registrar("pide_ocr")
def pide_ocr() -> list[str]:
    ruta = input("Ruta del PDF escaneado o foto (arrastralo acá o pegá la ruta): ").strip().strip('"')
    if not ruta:
        raise ValueError("hace falta la ruta del archivo")
    return [ruta, "--texto"]


def construir_comando(accion: dict, extra: list[str], workspace: str | None) -> list[str]:
    """Arma la línea de comando de una acción."""
    comando = [sys.executable, str(DIR_SCRIPTS / accion["script"])]
    comando += list(extra)
    if accion["workspace"] and workspace:
        comando += ["--workspace", workspace]
    return comando


def correr(accion: dict, extra: list[str], workspace: str | None) -> int:
    """Corre el script de la acción y devuelve su código de salida tal cual."""
    resultado = subprocess.run(construir_comando(accion, extra, workspace))
    return resultado.returncode


def mostrar_menu() -> None:
    print()
    print("Orquestador documental — qué querés hacer")
    print()
    for accion in ACCIONES:
        print(f"  {accion['numero']:>2}. {accion['etiqueta']}")
    print("   0. Salir")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--opcion",
        type=int,
        help="corre una acción sin menú (número de la lista)",
    )
    parser.add_argument("--selftest", action="store_true", help="prueba de humo; no toca nada")
    ws.agregar_argumento(parser)
    args, extra = parser.parse_known_args(argv)

    if args.selftest:
        return selftest()

    if args.opcion is not None:
        if args.opcion == 0:
            return 0
        accion = buscar_accion(args.opcion)
        if accion is None:
            print(f"ERROR: no existe la opción {args.opcion}", file=sys.stderr)
            return 1
        return correr(accion, extra, args.workspace)

    while True:
        mostrar_menu()
        eleccion = input("Opción: ").strip()
        if not eleccion:
            continue
        if eleccion == "0":
            return 0
        if not eleccion.isdigit():
            print("Opción inválida: escribí el número de la lista.")
            continue
        accion = buscar_accion(int(eleccion))
        if accion is None:
            print(f"No existe la opción {eleccion}: es 1 a {len(ACCIONES)}.")
            continue

        extra: list[str] = []
        if accion["pide"]:
            try:
                extra = PIDE[accion["pide"]]()
            except ValueError as error:
                print(f"No se hizo nada: {error}")
                continue
            except EOFError:
                print("\nSin entrada no hay nada que correr.")
                continue
        try:
            correr(accion, extra, args.workspace)
        except KeyboardInterrupt:
            print("\nCancelado.")


def buscar_accion(numero: int) -> dict | None:
    for accion in ACCIONES:
        if accion["numero"] == numero:
            return accion
    return None


def selftest() -> int:
    """Comprueba que cada acción apunte a un script real y que el passthrough funcione."""
    fallos = 0

    for accion in ACCIONES:
        if not (DIR_SCRIPTS / accion["script"]).is_file():
            print(f"FALLO: la acción {accion['numero']} apunta a un script inexistente: {accion['script']}")
            fallos += 1
        if accion["pide"] and accion["pide"] not in PIDE:
            print(f"FALLO: la acción {accion['numero']} pide '{accion['pide']}' y no existe")
            fallos += 1

    numeros = [accion["numero"] for accion in ACCIONES]
    if sorted(numeros) != numeros or len(set(numeros)) != len(numeros):
        print(f"FALLO: los números de acción no son consecutivos y únicos: {numeros}")
        fallos += 1

    if buscar_accion(0) is not None or buscar_accion(len(ACCIONES) + 1) is not None:
        print("FALLO: buscar_accion() acepta números fuera de la lista")
        fallos += 1

    if not tipos_declarativos():
        print("FALLO: no se descubren specs declarativos en herramientas/contratos/tipos/")
        fallos += 1

    # Passthrough del código de salida: el menú no lo toca.
    resultado = subprocess.run(
        [sys.executable, "-c", "import sys; sys.exit(3)"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
    )
    if resultado.returncode != 3:
        print(f"FALLO: el passthrough devolvió {resultado.returncode}; esperado 3")
        fallos += 1

    if fallos:
        print(f"\nselftest del menú: {fallos} fallo(s)")
        return 1
    print("selftest del menú: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
