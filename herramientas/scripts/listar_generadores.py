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

    validos, rotos = gu.descubrir_todos()

    def relativa(ruta: Path) -> str:
        try:
            return ruta.relative_to(gu.RAIZ).as_posix()
        except ValueError:
            return ruta.as_posix()

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not rotos,
                    "generadores": [
                        {
                            "nombre": g.nombre,
                            "tipos": list(g.tipos),
                            "script": g.script.name,
                            "comando": list(g.comando),
                            "descripcion": g.descripcion,
                            "carpeta": relativa(g.carpeta),
                        }
                        for g in validos
                    ],
                    "rotos": [
                        {"carpeta": relativa(r.carpeta), "error": r.error} for r in rotos
                    ],
                },
                ensure_ascii=False,
            )
        )
        return 1 if rotos else 0

    if not validos and not rotos:
        print(f"No hay generadores propios en {relativa(gu.DIR_GENERADORES)}.")
        print(
            "Si querés usar tu propia plantilla como código, creá una carpeta con "
            "un manifiesto 'generador.json' y tu script. "
            "Ver herramientas/docs/contrato-generador.md."
        )
        return 0

    if validos:
        print(f"Generadores propios del usuario ({relativa(gu.DIR_GENERADORES)}):\n")
        for g in validos:
            print(f"  {g.nombre}")
            if g.descripcion:
                print(f"    {g.descripcion}")
            print(f"    tipos    : {', '.join(g.tipos)}")
            print(f"    script   : {g.script.name}  ({' '.join(g.comando)})")
            print(f"    carpeta  : {relativa(g.carpeta)}")
            print()

    if rotos:
        print(f"Generadores con manifiesto inválido ({len(rotos)}):\n")
        for roto in rotos:
            print(f"  [ROTO] {relativa(roto.carpeta)}")
            print(f"    {roto.error}")
            print()
        print(
            "Los generadores rotos no bloquean la generación de otros tipos, "
            "pero ese generador no va a usarse hasta corregir su manifiesto."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
