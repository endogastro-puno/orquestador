#!/usr/bin/env python3
"""Lee documentos y devuelve su contenido de forma utilizable.

Convierte un insumo —`.docx`, `.pdf`, `.xlsx`, `.csv`, `.md`, `.txt`— en texto y
estructura, para que el agente trabaje sobre datos reales y no sobre suposiciones.

Formatos y dependencias:

| Formato | Cómo se lee | Dependencia |
| --- | --- | --- |
| `.docx` | OOXML directo (`zipfile` + `xml.etree`) | **ninguna** |
| `.pdf` | `pdfplumber`, o `pypdf` como respaldo | `requirements.txt` |
| `.xlsx` | `openpyxl` | `requirements.txt` |
| `.csv` | módulo `csv` | **ninguna** |
| `.md`, `.txt` | lectura directa | **ninguna** |

Nunca modifica el archivo: sólo lee. No escribe nada.

Uso::

    python herramientas/scripts/leer_documento.py usuario/datos/entrada/informe.docx
    python herramientas/scripts/leer_documento.py planilla.xlsx --json
    python herramientas/scripts/leer_documento.py contrato.pdf --texto

Contrato de salida (`--json`):

* siempre: `ok`, `formato`, `ruta`, `bytes`, `texto`, `metadatos`;
* `.docx`: `parrafos`, `tablas`;
* `.pdf`: `paginas` (una entrada por página, con `numero` y `texto`);
* `.xlsx`: `hojas` (una entrada por hoja, con `nombre` y `filas`).

Las claves que no aplican al formato no aparecen. `texto` es la versión plana,
lista para buscar o pasar a otro comando.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

RAIZ = Path(__file__).resolve().parents[2]

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DC = "{http://purl.org/dc/elements/1.1/}"
DCTERMS = "{http://purl.org/dc/terms/}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"

NS_CORE = {
    "titulo": DC + "title",
    "autor": DC + "creator",
    "creado": DCTERMS + "created",
    "modificado": DCTERMS + "modified",
    "ultimo_editor": CP + "lastModifiedBy",
}

SOPORTADOS = (".docx", ".pdf", ".xlsx", ".csv", ".md", ".txt")


def _texto_parrafo(parrafo: ElementTree.Element) -> str:
    """Texto de un `w:p`, respetando tabulaciones y saltos."""
    partes: list[str] = []
    for nodo in parrafo.iter():
        if nodo.tag == W + "t":
            partes.append(nodo.text or "")
        elif nodo.tag == W + "tab":
            partes.append("\t")
        elif nodo.tag in (W + "br", W + "cr"):
            partes.append("\n")
    return "".join(partes).strip()


def leer_docx(ruta: Path) -> dict[str, Any]:
    """Lee un `.docx` sin dependencias: es un ZIP con XML adentro."""
    with zipfile.ZipFile(ruta) as paquete:
        documento = ElementTree.fromstring(paquete.read("word/document.xml"))
        cuerpo = documento.find(W + "body")
        parrafos: list[str] = []
        tablas: list[list[list[str]]] = []
        if cuerpo is not None:
            for hijo in list(cuerpo):
                if hijo.tag == W + "p":
                    texto = _texto_parrafo(hijo)
                    if texto:
                        parrafos.append(texto)
                elif hijo.tag == W + "tbl":
                    filas = [
                        [_texto_parrafo(celda) for celda in fila.findall(W + "tc")]
                        for fila in hijo.findall(W + "tr")
                    ]
                    if filas:
                        tablas.append(filas)
        metadatos: dict[str, str] = {}
        try:
            nucleo = ElementTree.fromstring(paquete.read("docProps/core.xml"))
        except KeyError:
            nucleo = None
        if nucleo is not None:
            for clave, etiqueta in NS_CORE.items():
                valor = (nucleo.findtext(etiqueta) or "").strip()
                if valor:
                    metadatos[clave] = valor

    return {
        "formato": "docx",
        "metadatos": metadatos,
        "parrafos": parrafos,
        "tablas": tablas,
        "texto": "\n\n".join(parrafos),
    }


def leer_pdf(ruta: Path) -> dict[str, Any]:
    """Lee un `.pdf` con `pdfplumber` y, si no está, con `pypdf`."""
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        pdfplumber = None  # type: ignore[assignment]

    if pdfplumber is not None:
        with pdfplumber.open(ruta) as pdf:
            paginas = [
                {"numero": numero, "texto": (pagina.extract_text() or "")}
                for numero, pagina in enumerate(pdf.pages, start=1)
            ]
            metadatos = {
                str(clave): str(valor) for clave, valor in (pdf.metadata or {}).items() if valor
            }
    else:
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:
            raise ValueError(
                "leer un PDF necesita 'pdfplumber' o 'pypdf': "
                "python -m pip install -r requirements.txt"
            ) from None
        lector = PdfReader(str(ruta))
        paginas = [
            {"numero": numero, "texto": (pagina.extract_text() or "")}
            for numero, pagina in enumerate(lector.pages, start=1)
        ]
        metadatos = {
            str(clave): str(valor) for clave, valor in (lector.metadata or {}).items() if valor
        }

    sin_texto = all(not pagina["texto"].strip() for pagina in paginas)
    resultado: dict[str, Any] = {
        "formato": "pdf",
        "metadatos": metadatos,
        "paginas": paginas,
        "texto": "\n\n".join(pagina["texto"] for pagina in paginas),
    }
    if sin_texto:
        resultado["aviso"] = (
            "el PDF no tiene texto extraíble: parece escaneado. "
            "Hace falta OCR (Tesseract) antes de leerlo."
        )
    return resultado


def leer_xlsx(ruta: Path) -> dict[str, Any]:
    """Lee un `.xlsx` con `openpyxl`, en modo sólo lectura."""
    try:
        import openpyxl  # type: ignore
    except ImportError:
        raise ValueError(
            "leer un .xlsx necesita 'openpyxl': python -m pip install -r requirements.txt"
        ) from None

    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        hojas = []
        for hoja in libro.worksheets:
            filas = []
            for fila in hoja.iter_rows(values_only=True):
                if all(celda is None or str(celda).strip() == "" for celda in fila):
                    continue
                filas.append(["" if celda is None else str(celda) for celda in fila])
            hojas.append({"nombre": hoja.title, "filas": filas})
    finally:
        libro.close()

    bloques = []
    for hoja in hojas:
        bloques.append(f"## {hoja['nombre']}")
        bloques.extend("\t".join(fila) for fila in hoja["filas"])
    return {
        "formato": "xlsx",
        "metadatos": {"hojas": str(len(hojas))},
        "hojas": hojas,
        "texto": "\n".join(bloques),
    }


def leer_csv(ruta: Path) -> dict[str, Any]:
    """Lee un `.csv` respetando la convención del repositorio (UTF-8 con BOM opcional)."""
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        filas = [fila for fila in csv.reader(archivo) if any(celda.strip() for celda in fila)]
    return {
        "formato": "csv",
        "metadatos": {"filas": str(len(filas))},
        "filas": filas,
        "texto": "\n".join(",".join(fila) for fila in filas),
    }


def leer_texto(ruta: Path) -> dict[str, Any]:
    """Lee `.md` y `.txt` como texto plano."""
    texto = ruta.read_text(encoding="utf-8-sig")
    return {
        "formato": ruta.suffix.lower().lstrip("."),
        "metadatos": {"lineas": str(len(texto.splitlines()))},
        "texto": texto,
    }


LECTORES = {
    ".docx": leer_docx,
    ".pdf": leer_pdf,
    ".xlsx": leer_xlsx,
    ".csv": leer_csv,
    ".md": leer_texto,
    ".txt": leer_texto,
}


def leer(ruta: Path) -> dict[str, Any]:
    """Lee el documento y devuelve su contrato de salida completo."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise ValueError(f"no existe el archivo: {ruta}")
    formato = ruta.suffix.lower()
    if formato not in LECTORES:
        raise ValueError(
            f"formato '{formato}' no soportado. Soportados: {', '.join(SOPORTADOS)}"
        )
    resultado = LECTORES[formato](ruta)
    try:
        referencia = ruta.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        referencia = ruta.resolve().as_posix()
    return {
        "ok": True,
        "formato": resultado["formato"],
        "ruta": referencia,
        "bytes": ruta.stat().st_size,
        **resultado,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("ruta", help="documento a leer")
    parser.add_argument("--json", action="store_true", help="resultado completo como JSON")
    parser.add_argument("--texto", action="store_true", help="imprime sólo el texto plano")
    parser.add_argument(
        "--max-caracteres",
        type=int,
        default=0,
        help="recorta el texto en la salida humana (0 = sin límite)",
    )
    args = parser.parse_args(argv)

    try:
        resultado = leer(Path(args.ruta))
    except (ValueError, OSError, zipfile.BadZipFile, ElementTree.ParseError) as error:
        if args.json:
            print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.json:
        if args.max_caracteres > 0 and len(resultado["texto"]) > args.max_caracteres:
            resultado["texto"] = resultado["texto"][: args.max_caracteres]
            resultado["truncado"] = True
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0

    if args.texto:
        print(resultado["texto"])
        return 0

    print(f"{resultado['formato'].upper()}  {resultado['ruta']}  ({resultado['bytes']} bytes)")
    for clave, valor in resultado.get("metadatos", {}).items():
        print(f"  {clave}: {valor}")
    if "paginas" in resultado:
        print(f"  páginas: {len(resultado['paginas'])}")
    if "hojas" in resultado:
        print(f"  hojas: {', '.join(hoja['nombre'] for hoja in resultado['hojas'])}")
    if "parrafos" in resultado:
        print(f"  párrafos: {len(resultado['parrafos'])}  tablas: {len(resultado['tablas'])}")

    texto = resultado["texto"]
    if args.max_caracteres > 0 and len(texto) > args.max_caracteres:
        print(f"\n{texto[: args.max_caracteres]}\n[... texto recortado; usá --texto para verlo completo]")
    else:
        print(f"\n{texto}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
