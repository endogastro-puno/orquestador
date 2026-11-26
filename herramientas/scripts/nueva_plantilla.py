#!/usr/bin/env python3
"""Crea una plantilla inicial para un tipo de documento.

El usuario arranca de cero: todavía no tiene plantilla y quiere una base
sobria sobre la que trabajar. Este comando la crea en
``plantillas/propias/`` con la convención de nombres del repositorio::

    <tipo>-<variante>.<ext>

La plantilla es un punto de partida, no un documento terminado: contiene los
marcadores del orquestador (``{{titulo}}``, ``{{fecha}}``, ``{{cuerpo}}``)
y ningún dato de empresa. El membrete, el logo y los estilos los agrega el
usuario después, o los trae con ``instalar_plantilla.py`` si ya tiene una.

Formatos por tipo (el ``--formato`` opcional elige dentro de los válidos):

* la mayoría de los tipos: ``.docx`` (OOXML mínimo, sin dependencias) o ``.md``;
* ``reporte`` y ``cotizacion``: ``.xlsx`` (necesita ``openpyxl``).

Nunca sobrescribe: si ya existe una plantilla con ese nombre, el comando falla
y te dice cuál es.

Uso::

    python herramientas/scripts/nueva_plantilla.py --tipo informe
    python herramientas/scripts/nueva_plantilla.py --tipo reporte --formato xlsx --variante Base2026

Códigos de salida: ``0`` creada, ``1`` error (tipo o formato inválidos, colisión,
``openpyxl`` faltante para ``.xlsx``).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plantillas as pl  # noqa: E402
import workspace as ws  # noqa: E402

TIPOS_DOC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS_DOC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

CUERPO_DOC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{{titulo}}</w:t></w:r></w:p>
    <w:p><w:r><w:t>{{fecha}}</w:t></w:r></w:p>
    <w:p/>
    <w:p><w:r><w:t>{{cuerpo}}</w:t></w:r></w:p>
  </w:body>
</w:document>"""

PLANTILLA_MD = """# {{titulo}}

{{fecha}}

## {{seccion}}

{{cuerpo}}
"""


def crear_docx(destino: Path) -> None:
    """Escribe una plantilla `.docx` mínima y válida, sin dependencias."""
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as paquete:
        paquete.writestr("[Content_Types].xml", TIPOS_DOC)
        paquete.writestr("_rels/.rels", RELS_DOC)
        paquete.writestr("word/document.xml", CUERPO_DOC)


def crear_xlsx(destino: Path) -> None:
    """Escribe una plantilla `.xlsx` mínima con `openpyxl`."""
    try:
        import openpyxl  # type: ignore
    except ImportError:
        raise ValueError(
            "crear una plantilla .xlsx necesita 'openpyxl': "
            "python -m pip install -r requirements.txt "
            "(o usá --formato md, que no necesita nada)"
        ) from None

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Plantilla"
    hoja["A1"] = "{{titulo}}"
    hoja["A2"] = "{{fecha}}"
    hoja["A3"] = "{{columnas}}"
    libro.save(destino)


def crear_md(destino: Path) -> None:
    """Escribe la plantilla `.md` directamente."""
    destino.write_text(PLANTILLA_MD, encoding="utf-8")


CREADORES = {
    "docx": crear_docx,
    "xlsx": crear_xlsx,
    "md": crear_md,
}


def crear(tipo: str, variante: str, extension: str, espacio: Path, oficiales: bool = False) -> Path:
    """Crea la plantilla inicial; falla si ya existe."""
    extension = pl.validar(tipo, extension)
    destino = pl.carpeta_destino(espacio, oficiales) / pl.nombre(tipo, variante, extension)
    if destino.exists():
        raise ValueError(
            f"ya existe la plantilla {destino.name} en {destino.parent}. "
            "Nunca se sobrescribe: usá otra --variante o borrá la existente vos mismo."
        )
    destino.parent.mkdir(parents=True, exist_ok=True)
    CREADORES[extension](destino)
    return destino


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--tipo", help=f"tipo de documento; válidos: {', '.join(sorted(pl.TIPOS))}")
    parser.add_argument(
        "--variante",
        default="base",
        help="nombre de la variante dentro del tipo (por defecto: base)",
    )
    parser.add_argument(
        "--formato",
        help="extensión de la plantilla (por defecto: la primera válida del tipo)",
    )
    parser.add_argument(
        "--oficiales",
        action="store_true",
        help="crea en plantillas/oficiales/ en vez de plantillas/propias/",
    )
    parser.add_argument("--selftest", action="store_true", help="prueba de humo; no toca nada")
    ws.agregar_argumento(parser)
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.tipo:
        parser.error("hace falta --tipo")

    extension = args.formato or pl.extensiones_de(args.tipo)[0]
    espacio = ws.resolver(args.workspace)

    try:
        destino = crear(args.tipo, args.variante, extension, espacio, oficiales=args.oficiales)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Espacio de trabajo: {ws.mostrar(espacio)}")
    print(f"Plantilla creada: {destino}")
    print("Contiene los marcadores {{titulo}} {{fecha}} {{cuerpo}}; el estilo es tuyo.")
    return 0


def selftest() -> int:
    """Prueba de humo en un temporal; no toca el repositorio."""
    fallos = 0
    with tempfile.TemporaryDirectory() as temporal:
        base = Path(temporal)

        md = crear("informe", "Base", "md", base)
        if not md.is_file() or "{{titulo}}" not in md.read_text(encoding="utf-8"):
            print("FALLO crear(md) -> archivo faltante o sin marcadores")
            fallos += 1

        docx = crear("oficio", "Base", "docx", base)
        try:
            with zipfile.ZipFile(docx) as paquete:
                partes = set(paquete.namelist())
                if "word/document.xml" not in partes:
                    raise KeyError("word/document.xml")
                if b"{{titulo}}" not in paquete.read("word/document.xml"):
                    print("FALLO crear(docx) -> falta el marcador {{titulo}}")
                    fallos += 1
        except (zipfile.BadZipFile, KeyError):
            print("FALLO crear(docx) -> no es un .docx válido")
            fallos += 1

        try:
            crear("informe", "Base", "md", base)
        except ValueError:
            pass
        else:
            print("FALLO crear() -> la colisión no se rechazó")
            fallos += 1

        try:
            crear("reporte", "Base", "docx", base)
        except ValueError:
            pass
        else:
            print("FALLO crear('reporte', 'docx') -> no se rechazó")
            fallos += 1

    if fallos:
        print(f"\nselftest de nueva_plantilla: {fallos} fallo(s)")
        return 1
    print("selftest de nueva_plantilla: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
