#!/usr/bin/env python3
"""Inicializa la estructura de la zona del usuario.

Crea las carpetas de ``usuario/`` y copia cada contrato de
``herramientas/contratos/`` a su archivo real en ``usuario/datos/``.

Garantías de no intromisión:

* Nunca sobrescribe un archivo existente del usuario.
* Nunca modifica ni borra nada que ya esté en ``usuario/``.
* Es idempotente: se puede ejecutar tantas veces como haga falta.

Sólo usa la biblioteca estándar.

Uso:
    python herramientas/scripts/init_local.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_CONTRATOS = RAIZ / "herramientas" / "contratos"
DIR_DATOS_USUARIO = RAIZ / "usuario" / "datos"

CARPETAS_USUARIO = (
    "usuario/datos/organizacion",
    "usuario/datos/tablas",
    "usuario/datos/entrada",
    "usuario/plantillas/propias",
    "usuario/plantillas/oficiales",
    "usuario/generadores",
    "usuario/recursos/logos",
    "usuario/recursos/firmas",
    "usuario/entregables/word",
    "usuario/entregables/pdf",
    "usuario/entregables/excel",
    "usuario/entregables/markdown",
    "usuario/entregables/borradores",
)


def crear_carpetas() -> list[Path]:
    """Crea las carpetas de la zona del usuario que falten."""
    creadas: list[Path] = []
    for relativa in CARPETAS_USUARIO:
        destino = RAIZ / relativa
        if not destino.exists():
            destino.mkdir(parents=True, exist_ok=True)
            creadas.append(destino)
    return creadas


def copiar_contratos() -> tuple[list[Path], list[Path]]:
    """Copia los contratos sin archivo real. Devuelve (creados, respetados).

    La ruta se deriva por convención::

        herramientas/contratos/organizacion/entidad.csv.example
            -> usuario/datos/organizacion/entidad.csv
    """
    creados: list[Path] = []
    respetados: list[Path] = []
    for contrato in sorted(DIR_CONTRATOS.glob("**/*.example")):
        relativa = contrato.relative_to(DIR_CONTRATOS)
        real = DIR_DATOS_USUARIO / relativa.with_suffix("")
        if real.exists():
            respetados.append(real)
            continue
        real.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(contrato, real)
        creados.append(real)
    return creados, respetados


def main() -> int:
    print(f"Repositorio: {RAIZ}")
    print("Zona del usuario: usuario/ (nunca se modifica lo que ya existe)\n")

    carpetas = crear_carpetas()
    creados, respetados = copiar_contratos()

    print("Carpetas:")
    if carpetas:
        for ruta in carpetas:
            print(f"  creada     {ruta.relative_to(RAIZ).as_posix()}/")
    else:
        print("  todas ya existían")

    print("\nArchivos de datos:")
    if creados:
        for ruta in creados:
            print(f"  creado     {ruta.relative_to(RAIZ).as_posix()}")
    else:
        print("  ningún archivo nuevo")
    if respetados:
        print(f"  respetados {len(respetados)} archivo(s) que ya existían (no se tocaron)")

    if not creados and not carpetas:
        print("\nNada que hacer: la estructura del usuario ya estaba completa.")
    else:
        print(
            "\nSiguiente paso: el usuario completa los valores PENDIENTE en usuario/datos/"
            "\ny luego se valida con:"
            "\n  python herramientas/scripts/validar_datos.py"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
