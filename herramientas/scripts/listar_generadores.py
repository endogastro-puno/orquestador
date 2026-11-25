#!/usr/bin/env python3
"""Lista los generadores propios del usuario y los tipos que cubren.

Un generador propio es código del usuario: vive en ``usuario/generadores/``,
no se versiona y no lo modifica el agente. Este script sólo lo **lee**.

Uso::

    python herramientas/scripts/listar_generadores.py
    python herramientas/scripts/listar_generadores.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generadores_usuario as gu  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="resultado como JSON")
    args = parser.parse_args(argv)

    try:
        generadores = gu.descubrir()
    except ValueError as error:
        if args.json:
            print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "generadores": [
                        {
                            "nombre": g.nombre,
                            "tipos": list(g.tipos),
                            "script": g.script.name,
                            "comando": list(g.comando),
                            "descripcion": g.descripcion,
                            "carpeta": g.carpeta.as_posix(),
                        }
                        for g in generadores
                    ],
                },
                ensure_ascii=False,
            )
        )
        return 0

    if not generadores:
        print(f"No hay generadores propios en {gu.DIR_GENERADORES.as_posix()}.")
        print(
            "Si querés usar tu propia plantilla como código, creá una carpeta con "
            "un manifiesto 'generador.json' y tu script. "
            "Ver herramientas/docs/contrato-generador.md."
        )
        return 0

    print(f"Generadores propios del usuario ({gu.DIR_GENERADORES.as_posix()}):\n")
    for g in generadores:
        print(f"  {g.nombre}")
        if g.descripcion:
            print(f"    {g.descripcion}")
        print(f"    tipos    : {', '.join(g.tipos)}")
        print(f"    script   : {g.script.name}  ({' '.join(g.comando)})")
        print(f"    carpeta  : {g.carpeta.as_posix()}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
