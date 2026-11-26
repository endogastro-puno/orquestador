#!/usr/bin/env python3
"""Lee documentos y devuelve su contenido de forma utilizable.

Convierte un insumo —`.docx`, `.doc`, `.pdf`, `.xlsx`, `.xls`, `.csv`, `.md`,
`.txt`— en texto y estructura, para que el agente trabaje sobre datos reales y no
sobre suposiciones.

Formatos y dependencias:

| Formato | Cómo se lee | Dependencia |
| --- | --- | --- |
| `.docx`, `.docm` | OOXML directo (`zipfile` + `xml.etree`) | **ninguna** |
| `.pdf` | `pdfplumber`, o `pypdf` como respaldo | `requirements.txt` |
| `.xlsx`, `.xlsm` | `openpyxl` | `requirements.txt` |
| `.doc`, `.rtf`, `.odt` | LibreOffice → `.docx` en un temporal, y lector OOXML | `soffice` (LibreOffice) |
| `.xls`, `.ods` | LibreOffice → `.xlsx` en un temporal, y `openpyxl` | `soffice` + `openpyxl` |
| `.csv` | módulo `csv` | **ninguna** |
| `.md`, `.txt` | lectura directa | **ninguna** |
| `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`, `.webp` | OCR (`Pillow` + `pytesseract` + binario Tesseract) | opcional: ver `INSTALACION.md` |

Los formatos viejos de Office se convierten a un archivo temporal y se leen de
ahí: el original **nunca se modifica**. Si falta LibreOffice, el comando falla
diciendo exactamente qué instalar; no devuelve texto vacío como si el documento
no tuviera nada.

Nunca modifica el archivo: sólo lee. La conversión de formatos viejos escribe en
un temporal que se borra al terminar; en tus carpetas no escribe nada.

Uso::

    python herramientas/scripts/leer_documento.py usuario/datos/entrada/informe.docx
    python herramientas/scripts/leer_documento.py planilla.xlsx --json
    python herramientas/scripts/leer_documento.py contrato.pdf --texto
    python herramientas/scripts/leer_documento.py expediente-viejo.doc --texto
    python herramientas/scripts/leer_documento.py escaneo.png --texto

Contrato de salida (`--json`):

* siempre: `ok`, `formato`, `ruta`, `bytes`, `texto`, `metadatos`;
* `.docx`: `parrafos`, `tablas`;
* `.pdf`: `paginas` (una entrada por página, con `numero` y `texto`);
* `.xlsx`: `hojas` (una entrada por hoja, con `nombre` y `filas`);
* formatos viejos (`.doc`, `.xls`, `.rtf`, `.odt`, `.ods`): las claves del
  formato convertido, más `metadatos.convertido_con` y `convertido_a`;
* imágenes: `pixeles` en `metadatos` (ancho x alto).

Las claves que no aplican al formato no aparecen. `texto` es la versión plana,
lista para buscar o pasar a otro comando.

Códigos de salida: ``0`` leyó y devolvió texto, ``2`` leyó pero no hay texto
extraíble (PDF escaneado, imagen sin texto; con el aviso en la salida de
error), ``1`` error — incluida la imagen con OCR sin instalar, cuyo mensaje
dice exactamente qué falta.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
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

SOPORTADOS = (
    ".docx",
    ".docm",
    ".doc",
    ".rtf",
    ".odt",
    ".pdf",
    ".xlsx",
    ".xlsm",
    ".xls",
    ".ods",
    ".csv",
    ".md",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
)

# Formatos viejos o de otro paquete: se convierten a OOXML en un temporal y se
# leen con el lector de siempre. El original nunca se toca.
LEGACY = {
    ".doc": "docx",
    ".rtf": "docx",
    ".odt": "docx",
    ".xls": "xlsx",
    ".ods": "xlsx",
}

COMO_INSTALAR_LIBREOFFICE = (
    "winget install TheDocumentFoundation.LibreOffice  "
    "(o guardá el archivo como .docx/.xlsx desde Word o Excel)"
)


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


def leer_imagen(ruta: Path) -> dict[str, Any]:
    """Lee una imagen con OCR (`Pillow` + `pytesseract` + binario Tesseract).

    El OCR es opcional: sin él el comando falla con un mensaje que dice qué
    falta instalar, en vez de devolver texto vacío como si la imagen no
    tuviera nada.
    """
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError:
        raise ValueError(
            "leer una imagen necesita OCR: python -m pip install pytesseract pillow "
            "y el binario Tesseract (ver INSTALACION.md, sección OCR)"
        ) from None

    try:
        with Image.open(ruta) as imagen:
            pixeles = f"{imagen.width}x{imagen.height}"
            texto = (pytesseract.image_to_string(imagen) or "").strip()
    except pytesseract.TesseractNotFoundError:
        raise ValueError(
            "no se encuentra el binario 'tesseract': instalalo con "
            "'winget install tesseract-ocr.tesseract' (ver INSTALACION.md, sección OCR)"
        ) from None

    resultado: dict[str, Any] = {
        "formato": ruta.suffix.lower().lstrip("."),
        "metadatos": {"pixeles": pixeles, "ocr": "tesseract"},
        "texto": texto,
    }
    if not texto:
        resultado["aviso"] = (
            "la imagen no produjo texto: puede estar vacía, borrosa o con letra "
            "que el OCR no reconoce. Probá con una imagen más nítida."
        )
    return resultado


def _soffice() -> str | None:
    """Ruta al ejecutable de LibreOffice, o None si no está instalado."""
    ruta = shutil.which("soffice")
    if ruta:
        return ruta
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(variable)
        if base:
            candidato = Path(base) / "LibreOffice" / "program" / "soffice.exe"
            if candidato.is_file():
                return str(candidato)
    mac = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    if mac.is_file():
        return str(mac)
    return None


def _convertir_con_libreoffice(ruta: Path, destino: str, trabajo: Path) -> Path:
    """Convierte ``ruta`` a ``destino`` dentro de ``trabajo`` y devuelve la copia."""
    soffice = _soffice()
    if soffice is None:
        raise ValueError(
            f"leer un '{ruta.suffix.lower()}' necesita LibreOffice para convertir "
            f"a .{destino} (el original no se toca): {COMO_INSTALAR_LIBREOFFICE}"
        )

    # Perfil propio: si LibreOffice ya está abierto con el perfil del usuario,
    # la conversión headless se cuelga o falla.
    perfil = trabajo / "perfil"
    try:
        resultado = subprocess.run(
            [
                soffice,
                "--headless",
                "--norestore",
                f"-env:UserInstallation={perfil.as_uri()}",
                "--convert-to",
                destino,
                "--outdir",
                str(trabajo),
                str(ruta),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        raise ValueError(
            f"LibreOffice tardó más de 180 s en convertir {ruta.name}; "
            f"probá abrirlo y guardarlo como .{destino}"
        ) from None
    except OSError as error:
        raise ValueError(f"no se pudo ejecutar LibreOffice: {error}") from None

    convertido = trabajo / f"{ruta.stem}.{destino}"
    if not convertido.is_file() or convertido.stat().st_size == 0:
        # Algunos nombres con caracteres raros hacen que LibreOffice cambie el
        # nombre de salida: vale cualquier archivo con la extensión pedida.
        candidatos = sorted(trabajo.glob(f"*.{destino}"))
        convertido = candidatos[0] if candidatos else convertido
    if not convertido.is_file() or convertido.stat().st_size == 0:
        detalle = (resultado.stderr or resultado.stdout or "").strip()
        detalle = detalle.splitlines()[-1][:200] if detalle else "sin detalle"
        raise ValueError(
            f"LibreOffice no pudo convertir {ruta.name} a .{destino}: {detalle}"
        )
    return convertido


def leer_legacy(ruta: Path) -> dict[str, Any]:
    """Lee `.doc`, `.xls`, `.rtf`, `.odt` u `.ods` vía LibreOffice.

    Convierte a un temporal y delega en el lector OOXML. El original no se
    modifica; el resultado conserva el formato original para que el índice y
    el usuario sepan qué clase de archivo era.
    """
    formato = ruta.suffix.lower()
    destino = LEGACY[formato]
    with tempfile.TemporaryDirectory(prefix="orquestador-legacy-") as temporal:
        convertido = _convertir_con_libreoffice(ruta, destino, Path(temporal))
        resultado = (leer_docx if destino == "docx" else leer_xlsx)(convertido)

    metadatos = dict(resultado.get("metadatos") or {})
    metadatos["convertido_con"] = "libreoffice"
    metadatos["convertido_a"] = f".{destino}"
    return {
        **resultado,
        "formato": formato.lstrip("."),
        "metadatos": metadatos,
    }


LECTORES = {
    ".docx": leer_docx,
    ".docm": leer_docx,
    ".pdf": leer_pdf,
    ".xlsx": leer_xlsx,
    ".xlsm": leer_xlsx,
    ".csv": leer_csv,
    ".md": leer_texto,
    ".txt": leer_texto,
    ".png": leer_imagen,
    ".jpg": leer_imagen,
    ".jpeg": leer_imagen,
    ".tif": leer_imagen,
    ".tiff": leer_imagen,
    ".bmp": leer_imagen,
    ".webp": leer_imagen,
}
LECTORES.update({extension: leer_legacy for extension in LEGACY})


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
        "ruta": referencia,
        "bytes": ruta.stat().st_size,
        **resultado,
        # El formato es el del archivo que pasó el usuario: `.docm` sigue siendo
        # `.docm` aunque por dentro se lea como OOXML.
        "formato": formato.lstrip("."),
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

    aviso = resultado.get("aviso")

    # Un solo lugar aplica el recorte: si se duplicara por rama, --texto podría
    # ignorar --max-caracteres sin que nadie lo note.
    texto = resultado["texto"]
    recortado = False
    if args.max_caracteres > 0 and len(texto) > args.max_caracteres:
        texto = texto[: args.max_caracteres]
        recortado = True

    if args.json:
        resultado["texto"] = texto
        if recortado:
            resultado["truncado"] = True
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    elif args.texto:
        print(texto)
    else:
        print(f"{resultado['formato'].upper()}  {resultado['ruta']}  ({resultado['bytes']} bytes)")
        for clave, valor in resultado.get("metadatos", {}).items():
            print(f"  {clave}: {valor}")
        if "paginas" in resultado:
            print(f"  páginas: {len(resultado['paginas'])}")
        if "hojas" in resultado:
            print(f"  hojas: {', '.join(hoja['nombre'] for hoja in resultado['hojas'])}")
        if "parrafos" in resultado:
            print(f"  párrafos: {len(resultado['parrafos'])}  tablas: {len(resultado['tablas'])}")
        print(f"\n{texto}")
        if recortado:
            print(
                f"[... texto recortado a {args.max_caracteres} caracteres; "
                "subí --max-caracteres o usá --texto para verlo completo]"
            )

    if aviso:
        print(f"AVISO: {aviso}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
