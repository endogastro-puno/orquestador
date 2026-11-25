#!/usr/bin/env python3
"""Resuelve la ruta de un entregable dentro de la zona del usuario.

Formato de salida::

    usuario/entregables/<carpeta>/AAAA-MM-DD_<slug>.<ext>

El slug se calcula quitando tildes y reemplazando cualquier secuencia de
caracteres no alfanuméricos por un guion. Si la ruta ya existe, agrega ``-v2``,
``-v3``, etc. Crea la carpeta destino si falta.

Este script **nunca sobrescribe** un entregable existente: si el nombre está
ocupado, propone una versión nueva.

Sólo usa la biblioteca estándar.

Uso::

    python herramientas/scripts/nuevo_entregable.py --tipo word --nombre "Memorándum de horarios"
    python herramientas/scripts/nuevo_entregable.py --tipo excel --nombre "Tarifas 2026" --json
    python herramientas/scripts/nuevo_entregable.py --tipo borrador --nombre "Acta" --extension md
    python herramientas/scripts/nuevo_entregable.py --selftest

Tipos disponibles: ``word``, ``pdf``, ``excel``, ``markdown`` (o ``md``), ``borrador``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import unicodedata
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# tipo -> (carpeta dentro de usuario/entregables/, extensión por defecto)
TIPOS: dict[str, tuple[str, str]] = {
    "word": ("word", "docx"),
    "docx": ("word", "docx"),
    "pdf": ("pdf", "pdf"),
    "excel": ("excel", "xlsx"),
    "xlsx": ("excel", "xlsx"),
    "markdown": ("markdown", "md"),
    "md": ("markdown", "md"),
    "borrador": ("borradores", "docx"),
}

PATRON_NO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")


def slug(texto: str) -> str:
    """Convierte un texto libre en un slug seguro para nombres de archivo."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    limpio = PATRON_NO_ALFANUMERICO.sub("-", sin_tildes.lower())
    return limpio.strip("-")


def resolver(
    tipo: str,
    nombre: str,
    fecha: str | None = None,
    extension: str | None = None,
    base: Path | None = None,
) -> Path:
    """Devuelve la ruta absoluta libre para el entregable pedido."""
    clave = tipo.strip().lower()
    if clave not in TIPOS:
        raise ValueError(f"tipo desconocido '{tipo}'. Usá uno de: {', '.join(sorted(TIPOS))}")
    if fecha is None:
        fecha = date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        raise ValueError(f"fecha inválida '{fecha}': se espera AAAA-MM-DD")

    carpeta, extension_por_defecto = TIPOS[clave]
    ext = (extension or extension_por_defecto).lstrip(".").lower().strip()
    if not re.fullmatch(r"[a-z0-9]{1,10}", ext):
        raise ValueError(f"extensión inválida '{ext}'")

    cuerpo = slug(nombre)
    if not cuerpo:
        raise ValueError("el nombre no produce un slug válido; usá letras o números")

    raiz = base if base is not None else RAIZ
    destino = raiz / "usuario" / "entregables" / carpeta
    candidato = destino / f"{fecha}_{cuerpo}.{ext}"
    version = 2
    while candidato.exists():
        candidato = destino / f"{fecha}_{cuerpo}-v{version}.{ext}"
        version += 1
    return candidato


def selftest() -> int:
    """Comprueba slug y resolución de colisiones sin tocar el repositorio."""
    fallos = 0

    casos_slug = [
        ("Memorándum de Horarios", "memorandum-de-horarios"),
        ("Acta N° 12", "acta-n-12"),
        ("  Reporte   de   Ingresos  ", "reporte-de-ingresos"),
        ("Informe 2026/01", "informe-2026-01"),
        ("ÁÉÍÓÚ ñandú", "aeiou-nandu"),
        ("Cotización — EndoGastro", "cotizacion-endogastro"),
    ]
    for entrada, esperado in casos_slug:
        obtenido = slug(entrada)
        if obtenido != esperado:
            print(f"FALLO slug({entrada!r}) -> {obtenido!r}; esperado {esperado!r}")
            fallos += 1

    with tempfile.TemporaryDirectory() as temporal:
        base = Path(temporal)
        primera = resolver("word", "Memorándum de Horarios", "2026-11-25", base=base)
        esperada = (
            base / "usuario" / "entregables" / "word" / "2026-11-25_memorandum-de-horarios.docx"
        )
        if primera != esperada:
            print(f"FALLO resolver -> {primera}; esperado {esperada}")
            fallos += 1

        primera.parent.mkdir(parents=True, exist_ok=True)
        primera.write_text("x", encoding="utf-8")
        segunda = resolver("word", "Memorándum de Horarios", "2026-11-25", base=base)
        esperada_v2 = (
            base / "usuario" / "entregables" / "word" / "2026-11-25_memorandum-de-horarios-v2.docx"
        )
        if segunda != esperada_v2:
            print(f"FALLO colisión -> {segunda}; esperado {esperada_v2}")
            fallos += 1

        try:
            resolver("inventado", "x", base=base)
        except ValueError:
            pass
        else:
            print("FALLO: un tipo desconocido debería lanzar ValueError")
            fallos += 1

        try:
            resolver("word", "   ", base=base)
        except ValueError:
            pass
        else:
            print("FALLO: un nombre vacío debería lanzar ValueError")
            fallos += 1

    if fallos:
        print(f"\n{fallos} comprobación(es) fallaron.")
        return 1
    print("Selftest OK: slug, versiones y validaciones de entrada funcionan.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resuelve la ruta de un entregable con la convención del repositorio."
    )
    parser.add_argument("--tipo", help="word | pdf | excel | markdown | borrador")
    parser.add_argument("--nombre", help="nombre descriptivo del documento")
    parser.add_argument("--fecha", help="fecha AAAA-MM-DD (por defecto, hoy)")
    parser.add_argument("--extension", help="fuerza la extensión (por ejemplo md)")
    parser.add_argument("--json", action="store_true", help="salida JSON")
    parser.add_argument("--selftest", action="store_true", help="ejecuta comprobaciones internas")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.tipo or not args.nombre:
        parser.error("--tipo y --nombre son obligatorios (o usá --selftest)")

    try:
        ruta = resolver(args.tipo, args.nombre, args.fecha, args.extension)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    ruta.parent.mkdir(parents=True, exist_ok=True)

    if args.json:
        print(
            json.dumps(
                {
                    "ruta": ruta.as_posix(),
                    "relativa": ruta.relative_to(RAIZ).as_posix(),
                    "tipo": TIPOS[args.tipo.strip().lower()][0],
                    "extension": ruta.suffix.lstrip("."),
                },
                ensure_ascii=False,
            )
        )
    else:
        try:
            print(ruta.relative_to(RAIZ).as_posix())
        except ValueError:
            print(ruta.as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
