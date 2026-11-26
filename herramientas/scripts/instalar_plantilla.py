#!/usr/bin/env python3
"""Instala una plantilla que el usuario ya tiene en su espacio de trabajo.

El usuario ya tiene su plantilla —un `.docx` de la oficina, un `.xlsx` que usa
hace años— y quiere que el orquestador la use. Este comando la copia a
``plantillas/propias/`` (o ``plantillas/oficiales/`` con ``--oficiales``) con
la convención de nombres del repositorio::

    <tipo>-<variante>.<ext>

El original nunca se toca: se copia, no se mueve. El destino nunca se
sobrescribe: si ya existe una plantilla con ese nombre, el comando falla y te
dice cuál es. La extensión del archivo tiene que ser válida para el tipo
(un `reporte` no puede ser `.docx`); las combinaciones válidas están en
``herramientas/docs/tipos-de-documento.md``.

Es el contrato de ``init_local.py``: crea un archivo que no existe, nunca
edita uno existente.

Uso::

    python herramientas/scripts/instalar_plantilla.py --origen "C:\\Usuarios\\vo\\Documentos\\membrete.docx" --tipo oficio --variante Corporativa
    python herramientas/scripts/instalar_plantilla.py --origen planilla.xlsx --tipo reporte --workspace D:\\clientes\\clinica-a

Códigos de salida: ``0`` instalada, ``1`` error (origen inexistente, tipo o
extensión inválidos, colisión).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plantillas as pl  # noqa: E402
import workspace as ws  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--origen", help="ruta de la plantilla del usuario (la que ya tiene)")
    parser.add_argument("--tipo", help=f"tipo de documento; válidos: {', '.join(sorted(pl.TIPOS))}")
    parser.add_argument(
        "--variante",
        default="base",
        help="nombre de la variante dentro del tipo (por defecto: base)",
    )
    parser.add_argument(
        "--oficiales",
        action="store_true",
        help="instala en plantillas/oficiales/ en vez de plantillas/propias/",
    )
    parser.add_argument("--selftest", action="store_true", help="prueba de humo; no toca nada")
    ws.agregar_argumento(parser)
    args = parser.parse_args(argv)

    if args.selftest:
        return pl.selftest()

    if not args.origen or not args.tipo:
        parser.error("hace falta --origen y --tipo")

    espacio = ws.resolver(args.workspace)

    try:
        destino = pl.instalar(
            Path(args.origen).expanduser(),
            espacio,
            args.tipo,
            args.variante,
            oficiales=args.oficiales,
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Espacio de trabajo: {ws.mostrar(espacio)}")
    print(f"Plantilla instalada: {destino}")
    print("El original no se modificó: se copió, no se movió.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
