#!/usr/bin/env python3
"""Resuelve el espacio de trabajo del usuario.

El **espacio de trabajo** es la carpeta que contiene la zona del usuario:

    <espacio>/
      datos/
      plantillas/
      generadores/
      recursos/
      entregables/

Por defecto es ``<repo>/usuario``. Se puede apuntar a otra carpeta con
``--workspace <ruta>`` o con la variable de entorno ``ORQUESTADOR_WORKSPACE``.

Eso permite usar la herramienta con los datos en otro lado —otro cliente, otro
disco, una carpeta sincronizada— sin copiar el repositorio ni tocar sus
archivos. El orden de resolución es fijo:

1. ``--workspace`` (relativa al directorio desde donde corrés el comando)
2. ``ORQUESTADOR_WORKSPACE``
3. ``<repo>/usuario``

Este módulo sólo resuelve rutas: no crea, no valida y no escribe nada.
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
VARIABLE_ENTORNO = "ORQUESTADOR_WORKSPACE"

# Subcarpetas que forman la zona del usuario, en el orden en que se crean.
SUBCARPETAS = (
    "datos/organizacion",
    "datos/tablas",
    "datos/entrada",
    "plantillas/propias",
    "plantillas/oficiales",
    "generadores",
    "recursos/logos",
    "recursos/firmas",
    "entregables/word",
    "entregables/pdf",
    "entregables/excel",
    "entregables/markdown",
    "entregables/borradores",
)


def resolver(explicito: str | Path | None = None, base: Path | None = None) -> Path:
    """Devuelve el espacio de trabajo según la precedencia documentada.

    ``base`` permite sustituir la raíz del repositorio en las pruebas; no se
    expone por línea de comandos.
    """
    if explicito:
        return Path(explicito).expanduser().resolve()
    del_entorno = os.environ.get(VARIABLE_ENTORNO)
    if del_entorno:
        return Path(del_entorno).expanduser().resolve()
    raiz = Path(base).resolve() if base is not None else RAIZ
    return raiz / "usuario"


def datos(espacio: Path) -> Path:
    return Path(espacio) / "datos"


def generadores(espacio: Path) -> Path:
    return Path(espacio) / "generadores"


def entregables(espacio: Path) -> Path:
    return Path(espacio) / "entregables"


def agregar_argumento(parser) -> None:
    """Agrega ``--workspace`` con el mismo texto en todos los comandos."""
    parser.add_argument(
        "--workspace",
        help=(
            "carpeta que contiene datos/ plantillas/ generadores/ recursos/ entregables/ "
            f"(por defecto: <repo>/usuario, o ${VARIABLE_ENTORNO})"
        ),
    )


def mostrar(ruta: Path, espacio: Path | None = None) -> str:
    """Ruta legible: nunca una ruta absoluta si se puede evitar.

    Prueba, en orden: relativa al repositorio, al espacio de trabajo y a la
    carpeta que contiene el espacio de trabajo.
    """
    ruta = Path(ruta).resolve()
    bases = [RAIZ]
    if espacio is not None:
        espacio = Path(espacio).resolve()
        bases.extend([espacio, espacio.parent])
    for base in bases:
        try:
            return ruta.relative_to(base).as_posix()
        except ValueError:
            continue
    return ruta.as_posix()
