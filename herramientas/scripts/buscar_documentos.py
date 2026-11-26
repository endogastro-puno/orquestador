#!/usr/bin/env python3
"""Busca en el índice de documentos: nombres y contenido, sin caminar carpetas.

Es la otra mitad del mapa: ``indexar_documentos.py`` construye el índice una
vez; este comando lo consulta en milisegundos. Busca por nombre **y por el
texto de adentro** de los Word y PDF indexados, sin acentos ni mayúsculas,
con filtros por tipo y carpeta. Y responde la pregunta típica del usuario de
PDFs escaneados: dónde están::

    python herramientas/scripts/buscar_documentos.py "cotización"
    python herramientas/scripts/buscar_documentos.py --escaneados
    python herramientas/scripts/buscar_documentos.py contrato --tipo docx,pdf --raiz folder-principal

Sin consulta, lista lo que pida el filtro (por ejemplo, todos los PDF
escaneados). Con ``--solo-nombres`` no busca en el texto ni en el OCR: sólo
en los nombres de archivo. Si el índice se armó con ``--con-ocr``, la
búsqueda también encuentra el texto reconocido (`donde: ocr`).

La ruta de cada resultado es relativa a su raíz indexada; la raíz se
identifica una sola vez en el encabezado, como hace ``leer_documento.py``
con los archivos fuera del repositorio. El índice vive en
``<espacio>/indice/`` (nunca se versiona: contiene texto de documentos
privados).

Códigos de salida: ``0`` hubo resultados, ``1`` no hubo, no existe el índice
o falló el filtro.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import indexar_documentos as ix  # noqa: E402
import workspace as ws  # noqa: E402

PATRON_NO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para buscar sin importar cómo se escriba."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return sin_tildes.lower()


def cargar_indices(espacio: Path) -> list[dict]:
    """Todos los índices del espacio, con su raíz registrada."""
    carpeta = Path(espacio) / "indice"
    if not carpeta.is_dir():
        return []
    indices = []
    for ruta in sorted(carpeta.glob("*.json")):
        indice = ix.cargar(ruta)
        if indice and "archivos" in indice:
            indices.append(indice)
    return indices


def _snippet(texto: str, consulta_normalizada: str) -> str | None:
    """Pedacito de contexto alrededor del match de contenido."""
    if not texto:
        return None
    posicion = normalizar(texto).find(consulta_normalizada)
    if posicion < 0:
        return None
    desde = max(0, posicion - 60)
    prefijo = "…" if desde > 0 else ""
    recorte = texto[desde : posicion + 120].replace("\n", " ").strip()
    if not recorte:
        return None
    return f"{prefijo}{recorte}…"


def _fecha(mtime: int | None) -> str:
    if not mtime:
        return "?"
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")


def _kb(bytes_: int | None) -> str:
    if bytes_ is None:
        return "?"
    if bytes_ >= 1024 * 1024:
        return f"{bytes_ / (1024 * 1024):.1f} MB"
    return f"{max(1, bytes_ // 1024)} KB"


def buscar(
    indices: list[dict],
    consulta: str = "",
    tipos: tuple[str, ...] = (),
    carpeta: str = "",
    escaneados: bool = False,
    solo_nombres: bool = False,
    maximo: int = 30,
) -> tuple[list[dict], int]:
    """Devuelve (resultados, total de coincidencias antes del recorte)."""
    busqueda = normalizar(consulta) if consulta else ""
    resultados: list[dict] = []
    total = 0

    for indice in indices:
        raiz = indice.get("raiz", "?")
        for entrada in indice.get("archivos", []):
            if tipos and entrada.get("extension", "").lstrip(".") not in tipos:
                continue
            if carpeta and normalizar(carpeta) not in normalizar(entrada.get("carpeta", "")):
                continue
            if escaneados and not entrada.get("escaneado"):
                continue

            donde = None
            snippet = None
            if busqueda:
                if busqueda in normalizar(entrada.get("nombre", "")):
                    donde = "nombre"
                elif not solo_nombres and busqueda in normalizar(entrada.get("texto") or ""):
                    donde = "texto"
                    snippet = _snippet(entrada.get("texto") or "", busqueda)
                elif not solo_nombres and busqueda in normalizar(entrada.get("texto_ocr") or ""):
                    donde = "ocr"
                    snippet = _snippet(entrada.get("texto_ocr") or "", busqueda)
                if donde is None:
                    continue
            elif consulta == "" and (tipos or carpeta or escaneados):
                pass  # sin consulta con filtros: listar los que pasan
            else:
                continue  # sin consulta y sin filtros no hay nada que listar

            total += 1
            if len(resultados) < maximo:
                resultados.append(
                    {
                        "raiz": raiz,
                        "ruta": entrada["ruta"],
                        "nombre": entrada["nombre"],
                        "extension": entrada.get("extension"),
                        "documento": entrada.get("documento", True),
                        "escaneado": bool(entrada.get("escaneado")),
                        "con_ocr": bool(entrada.get("texto_ocr")),
                        "bytes": entrada.get("bytes"),
                        "fecha": _fecha(entrada.get("mtime")),
                        "donde": donde,
                        "snippet": snippet,
                        "error": entrada.get("error"),
                    }
                )
    return resultados, total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("consulta", nargs="?", default="", help="texto a buscar (omitilo para sólo listar)")
    parser.add_argument("--raiz", help="sólo índices cuya raíz contenga este texto")
    parser.add_argument("--tipo", help="filtra extensiones, separadas por coma: docx,pdf,md")
    parser.add_argument("--carpeta", help="sólo archivos cuya carpeta contenga este texto")
    parser.add_argument("--escaneados", action="store_true", help="sólo PDF escaneados (sin texto extraíble)")
    parser.add_argument("--solo-nombres", action="store_true", help="no busca en el texto, sólo en los nombres")
    parser.add_argument("--max", type=int, default=30, help="máximo de resultados a mostrar (por defecto: 30)")
    parser.add_argument("--json", action="store_true", help="resultados como JSON")
    parser.add_argument("--selftest", action="store_true", help="prueba de humo; no toca nada")
    ws.agregar_argumento(parser)
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    espacio = ws.resolver(args.workspace)
    indices = cargar_indices(espacio)
    if args.raiz:
        indices = [indice for indice in indices if normalizar(args.raiz) in normalizar(indice.get("raiz", ""))]
    if not indices:
        print(
            "ERROR: no hay índice que consultar. Primero mapeá una carpeta:\n"
            "  python herramientas/scripts/indexar_documentos.py --ruta <carpeta>",
            file=sys.stderr,
        )
        return 1

    tipos = tuple(extension.strip().lower().lstrip(".") for extension in (args.tipo or "").split(",") if extension.strip())
    if not args.consulta and not tipos and not args.carpeta and not args.escaneados:
        print(
            "ERROR: nada que buscar. Pasá una consulta, o un filtro (--tipo, --carpeta, --escaneados).",
            file=sys.stderr,
        )
        return 1
    resultados, total = buscar(
        indices,
        consulta=args.consulta,
        tipos=tipos,
        carpeta=args.carpeta,
        escaneados=args.escaneados,
        solo_nombres=args.solo_nombres,
        maximo=max(1, args.max),
    )

    if not resultados:
        mensaje = f"sin resultados para '{args.consulta}'" if args.consulta else "sin resultados para el filtro"
        print(f"AVISO: {mensaje}. Probá otra palabra o re-indexá la raíz si cambiaron los archivos.")
        return 1

    if args.json:
        print(json.dumps({"total": total, "resultados": resultados}, ensure_ascii=False, indent=2))
        return 0

    print(f"Índices consultados: {len(indices)}  ·  coincidencias: {total}")
    for indice in indices:
        print(f"  raíz: {indice.get('raiz', '?')}")
    print()
    for posicion, resultado in enumerate(resultados, start=1):
        etiquetas = [resultado["extension"] or "?", _kb(resultado["bytes"]), resultado["fecha"]]
        if resultado["escaneado"]:
            etiquetas.append("escaneado: sí, necesita OCR" if not resultado["con_ocr"] else "escaneado: sí, con OCR")
        if resultado["donde"] == "ocr":
            etiquetas.append("match en OCR")
        if resultado["error"]:
            etiquetas.append(f"error de lectura: {resultado['error']}")
        print(f"[{posicion}] {resultado['ruta']}  ·  {'  ·  '.join(etiquetas)}")
        if resultado["snippet"]:
            origen = "ocr" if resultado["donde"] == "ocr" else "texto"
            print(f"    {origen}: “{resultado['snippet']}”")
    if total > len(resultados):
        print(f"\n[... {total - len(resultados)} coincidencia(s) más: subí --max]")
    return 0


def selftest() -> int:
    """Prueba de humo en un temporal; no toca el repositorio."""
    fallos = 0
    import tempfile

    with tempfile.TemporaryDirectory() as temporal:
        base = Path(temporal)
        raiz = base / "documentos"
        (raiz / "clientes").mkdir(parents=True)
        (raiz / "clientes").joinpath("Cotización ACME.txt").write_text(
            "Cotización de servicios de mantenimiento para ACME, 2026.", encoding="utf-8"
        )
        (raiz / "varios").mkdir()
        (raiz / "varios").joinpath("nota.md").write_text("# Nota\n\nSin contenido relevante.", encoding="utf-8")

        espacio = base / "espacio"
        ix.indexar(raiz, espacio)
        indices = cargar_indices(espacio)
        if len(indices) != 1:
            print(f"FALLO: se esperaba 1 índice, hay {len(indices)}")
            fallos += 1

        # Buscar sin tildes ni mayúsculas, en el nombre y en el texto.
        resultados, total = buscar(indices, consulta="cotizacion")
        rutas = {resultado["ruta"] for resultado in resultados}
        if "clientes/Cotización ACME.txt" not in rutas or total != 1:
            print(f"FALLO búsqueda sin tildes -> {resultados}")
            fallos += 1

        resultados, _ = buscar(indices, consulta="mantenimiento")
        if not resultados or resultados[0]["donde"] != "texto" or not resultados[0]["snippet"]:
            print(f"FALLO búsqueda de contenido -> {resultados}")
            fallos += 1

        # Filtro por tipo y listing sin consulta.
        resultados, _ = buscar(indices, tipos=("md",))
        if {resultado["ruta"] for resultado in resultados} != {"varios/nota.md"}:
            print(f"FALLO filtro --tipo md -> {resultados}")
            fallos += 1

        resultados, _ = buscar(indices, consulta="no-existe-ni-de-lejos")
        if resultados:
            print("FALLO: la búsqueda inexistente devolvió resultados")
            fallos += 1

        # Sólo nombres: el texto no matchea, el nombre sí.
        resultados, _ = buscar(indices, consulta="nota", solo_nombres=True)
        if {resultado["ruta"] for resultado in resultados} != {"varios/nota.md"}:
            print(f"FALLO --solo-nombres -> {resultados}")
            fallos += 1

        # OCR: el texto reconocido también se busca (donde: ocr).
        indices_ocr = [
            {
                "raiz": str(raiz),
                "archivos": [
                    {
                        "ruta": "escaneo.pdf",
                        "nombre": "escaneo.pdf",
                        "carpeta": ".",
                        "extension": ".pdf",
                        "documento": True,
                        "escaneado": True,
                        "texto": "",
                        "texto_ocr": "CONTRATO RECONOCIDO POR OCR",
                        "mtime": 1_700_000_000,
                    }
                ],
            }
        ]
        resultados, _ = buscar(indices_ocr, consulta="contrato")
        if not resultados or resultados[0]["donde"] != "ocr" or not resultados[0]["snippet"]:
            print(f"FALLO búsqueda en OCR -> {resultados}")
            fallos += 1

    if fallos:
        print(f"\nselftest de búsqueda: {fallos} fallo(s)")
        return 1
    print("selftest de búsqueda: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
