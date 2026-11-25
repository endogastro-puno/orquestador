#!/usr/bin/env python3
"""Inicializa la estructura de la zona del usuario.

Crea las carpetas del espacio de trabajo y copia cada contrato de
``herramientas/contratos/`` a su archivo real en ``<espacio>/datos/``.

El espacio de trabajo por defecto es ``<repo>/usuario``; con ``--workspace``
se puede preparar la estructura en otra carpeta y trabajar desde ahí.

Garantías de no intromisión:

* Nunca sobrescribe un archivo existente del usuario.
* Nunca modifica ni borra nada que ya esté en la zona del usuario.
* Es idempotente: se puede ejecutar tantas veces como haga falta.

Sólo usa la biblioteca estándar.

Uso:
    python herramientas/scripts/init_local.py
    python herramientas/scripts/init_local.py --workspace D:\\clientes\\clinica-a
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace as ws  # noqa: E402

RAIZ = ws.RAIZ
DIR_CONTRATOS = RAIZ / "herramientas" / "contratos"


def crear_carpetas(espacio: Path) -> list[Path]:
    """Crea las carpetas de la zona del usuario que falten."""
    creadas: list[Path] = []
    for relativa in ws.SUBCARPETAS:
        destino = espacio / relativa
        if not destino.exists():
            destino.mkdir(parents=True, exist_ok=True)
            creadas.append(destino)
    return creadas


def copiar_contratos(espacio: Path) -> tuple[list[Path], list[Path]]:
    """Copia los contratos sin archivo real. Devuelve (creados, respetados).

    La ruta se deriva por convención::

        herramientas/contratos/organizacion/entidad.csv.example
            -> <espacio>/datos/organizacion/entidad.csv
    """
    creados: list[Path] = []
    respetados: list[Path] = []
    for contrato in sorted(DIR_CONTRATOS.glob("**/*.example")):
        relativa = contrato.relative_to(DIR_CONTRATOS)
        real = espacio / "datos" / relativa.with_suffix("")
        if real.exists():
            respetados.append(real)
            continue
        real.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(contrato, real)
        creados.append(real)
    return creados, respetados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ws.agregar_argumento(parser)
    args = parser.parse_args(argv)
    espacio = ws.resolver(args.workspace)

    print(f"Repositorio: {RAIZ}")
    print(f"Espacio de trabajo: {ws.mostrar(espacio)}\n")

    carpetas = crear_carpetas(espacio)
    creados, respetados = copiar_contratos(espacio)

    print("Carpetas:")
    if carpetas:
        for ruta in carpetas:
            print(f"  creada     {ws.mostrar(ruta, espacio)}/")
    else:
        print("  todas ya existían")

    print("\nArchivos de datos:")
    if creados:
        for ruta in creados:
            print(f"  creado     {ws.mostrar(ruta, espacio)}")
    else:
        print("  ningún archivo nuevo")
    if respetados:
        print(f"  respetados {len(respetados)} archivo(s) que ya existían (no se tocaron)")

    args_ws = f" --workspace {espacio}" if espacio != RAIZ / "usuario" else ""
    if not creados and not carpetas:
        print("\nNada que hacer: la estructura del usuario ya estaba completa.")
    else:
        print(
            f"\nSiguiente paso: el usuario completa los valores PENDIENTE en "
            f"{ws.mostrar(espacio / 'datos', espacio)}/"
            "\ny luego se valida con:"
            f"\n  python herramientas/scripts/validar_datos.py{args_ws}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
