#!/usr/bin/env python3
"""Comprueba de punta a punta que el motor genera un documento.

Crea un espacio de trabajo temporal (datos, un tipo de prueba y un generador
propio mínimo), corre el motor y verifica el archivo producido. **No toca
`usuario/` ni deja archivos en el repositorio.**

Corre los dos caminos del motor, por separado:

* ``renderizador-docx``: necesita Node.js y ``node_modules`` (la librería `docx`).
* ``generador-usuario``: sólo necesita Python.

Si un camino no puede correr por una dependencia ausente, lo informa como
**OMITIDO** y sigue. Si un camino corre y falla, el script falla.

Uso::

    python herramientas/scripts/selftest.py
    python herramientas/scripts/selftest.py --json

Códigos de salida: ``0`` todo lo que corrió salió bien, ``1`` alguna falla.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generar_documento as motor  # noqa: E402

SPEC = {
    "tipo": "prueba",
    "titulo": "Prueba de humo",
    "formato": "docx",
    "datos": {"entidad": "organizacion/entidad.csv"},
    "constantes": {},
    "bloques": [
        {"tipo": "portada", "lineas": [{"texto": "{{entidad.razon_social}}", "negrita": True}]},
        {"tipo": "titulo", "nivel": 1, "texto": "I. Objeto", "indice": True},
        {"tipo": "parrafo", "texto": "Documento de prueba generado por selftest.py."},
        {
            "tipo": "tabla",
            "encabezado": ["Código", "Monto"],
            "filas": [["P-001", "10.00"], ["P-002", "20.00"]],
        },
        {"tipo": "firma", "cargo": "Gerente", "entidad": "{{entidad.razon_social}}", "texto": "Firma"},
    ],
}

GENERADOR = '''\
import json
import pathlib
import sys

argumentos = sys.argv[1:]
entrada = argumentos[argumentos.index("--entrada") + 1]
payload = json.loads(pathlib.Path(entrada).read_text(encoding="utf-8"))
destino = pathlib.Path(payload["salida"])
destino.parent.mkdir(parents=True, exist_ok=True)
lineas = [payload["titulo"], f"tipo={payload['tipo']}", f"bloques={len(payload['bloques'])}"]
destino.write_text("\\n".join(lineas) + "\\n", encoding="utf-8")
'''

MANIFIESTO = {"nombre": "prueba", "tipos": ["*"], "script": "generador.py"}


def preparar(base: Path) -> None:
    """Crea el espacio de trabajo temporal mínimo."""
    (base / "usuario" / "entregables" / "word").mkdir(parents=True, exist_ok=True)
    datos = base / "datos" / "organizacion"
    datos.mkdir(parents=True, exist_ok=True)
    (datos / "entidad.csv").write_text(
        "clave,valor\nrazon_social,ACME S.A.C.\nnombre_comercial,ACME\n", encoding="utf-8"
    )
    specs = base / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / "prueba.json").write_text(
        json.dumps(SPEC, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def preparar_generador(base: Path) -> None:
    """Crea un generador propio mínimo, del tamaño justo para probar el contrato."""
    carpeta = base / "usuario" / "generadores" / "prueba"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "generador.json").write_text(
        json.dumps(MANIFIESTO, ensure_ascii=False), encoding="utf-8"
    )
    (carpeta / "generador.py").write_text(GENERADOR, encoding="utf-8")


def correr(base: Path, nombre: str, extra: list[str]) -> tuple[str, str]:
    """Corre el motor y devuelve (estado, detalle).

    El motor imprime su propio JSON; acá se lo descarta para que la salida de
    esta prueba de humo sea un único documento JSON válido.
    """
    salida = base / "usuario" / "entregables" / "word" / f"{nombre}.docx"
    with contextlib.redirect_stdout(io.StringIO()):
        codigo = motor.main(
            [
                "--tipo",
                "prueba",
                "--datos",
                str(base / "datos"),
                "--salida",
                str(salida),
                "--json",
                *extra,
            ]
        )
    if codigo != 0:
        return "FALLA", f"el motor devolvió {codigo}"
    if not salida.is_file() or salida.stat().st_size == 0:
        return "FALLA", "no se produjo el archivo"
    return "OK", f"{salida.stat().st_size} bytes"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="resultado como JSON")
    args = parser.parse_args(argv)

    resultados: list[dict[str, str]] = []

    raiz_original, specs_original = motor.RAIZ, motor.DIR_SPECS
    with tempfile.TemporaryDirectory(prefix="orquestador-selftest-") as temporal:
        base = Path(temporal)
        preparar(base)
        preparar_generador(base)
        motor.RAIZ = base
        motor.DIR_SPECS = base / "specs"
        try:
            if shutil.which("node") and (raiz_original / "node_modules" / "docx").is_dir():
                estado, detalle = correr(base, "renderizador", ["--sin-generador"])
            else:
                estado, detalle = "OMITIDO", "falta Node.js o node_modules (npm install)"
            resultados.append({"camino": "renderizador-docx", "estado": estado, "detalle": detalle})

            estado, detalle = correr(base, "generador", [])
            resultados.append({"camino": "generador-usuario", "estado": estado, "detalle": detalle})
        finally:
            motor.RAIZ, motor.DIR_SPECS = raiz_original, specs_original

    fallas = [r for r in resultados if r["estado"] == "FALLA"]

    if args.json:
        print(
            json.dumps(
                {"ok": not fallas, "resultados": resultados}, ensure_ascii=False, indent=2
            )
        )
    else:
        print("Prueba de humo del motor (espacio temporal, no toca usuario/)\n")
        for resultado in resultados:
            print(f"  {resultado['estado']:<8} {resultado['camino']:<20} {resultado['detalle']}")
        if fallas:
            print(f"\nResultado: {len(fallas)} camino(s) con falla.")
        else:
            print("\nResultado: el motor funciona en los caminos que pudieron correr.")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
