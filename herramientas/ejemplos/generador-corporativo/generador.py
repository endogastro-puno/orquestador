#!/usr/bin/env python3
"""Ejemplo de generador propio del usuario.

Este archivo es CÓDIGO DEL USUARIO, no del proyecto. Es un ejemplo para
copiar: muestra el contrato completo que el motor respeta.

Contrato (resumido):

* el motor arma un ``payload.json`` y lo pasa con ``--entrada``;
* el generador escribe el archivo final en ``payload["salida"]``;
* termina con código 0 si todo salió bien, con otro código si falló.

Qué hace este ejemplo: aplica una identidad visual corporativa (tipografía,
color de títulos, membrete con logo, pie con número de página) a cualquier
tipo de documento. El contenido ya viene resuelto por el motor: acá no se
redacta ni se calculan datos.

Uso:

    1. copiá esta carpeta a ``usuario/generadores/<tu-nombre>/``
    2. ajustá ``generador.json`` (nombre, tipos, script)
    3. ``python -m pip install python-docx``
    4. ``python herramientas/scripts/generar_documento.py --tipo manual``

El motor corre el generador con la raíz del repositorio como directorio de
trabajo, así que ``payload["salida"]`` es una ruta relativa a esa raíz.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

AZUL = RGBColor(0x1F, 0x38, 0x64)
AZUL_HEX = "D9E2F3"
GRIS_HEX = "F2F2F2"
FUENTE = "Arial"
MARGEN = Cm(2.5)


def sombrear(celda, color: str) -> None:
    """Pinta el fondo de una celda (python-docx no lo expone)."""
    tc_pr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def campo_pagina(parrafo) -> None:
    """Inserta el campo PAGE (número de página) en un párrafo."""
    run = parrafo.add_run()
    inicio = OxmlElement("w:fldChar")
    inicio.set(qn("w:fldCharType"), "begin")
    instruccion = OxmlElement("w:instrText")
    instruccion.set(qn("xml:space"), "preserve")
    instruccion.text = "PAGE"
    fin = OxmlElement("w:fldChar")
    fin.set(qn("w:fldCharType"), "end")
    run._r.append(inicio)
    run._r.append(instruccion)
    run._r.append(fin)


def aplicar_estilos(documento: Document) -> None:
    """Tipografía y color de títulos: la identidad de la empresa."""
    normal = documento.styles["Normal"]
    normal.font.name = FUENTE
    normal.font.size = Pt(11)

    for nombre, tamano in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 12)):
        estilo = documento.styles[nombre]
        estilo.font.name = FUENTE
        estilo.font.size = Pt(tamano)
        estilo.font.color.rgb = AZUL
        estilo.font.bold = True


def agregar_membrete(seccion, payload: dict) -> None:
    """Logo y razón social en el encabezado, si el usuario los provee."""
    entidad = payload.get("entidad") or {}
    encabezado = seccion.header.paragraphs[0]
    encabezado.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    logos = sorted(Path("usuario/recursos/logos").glob("*"))
    if logos:
        try:
            encabezado.add_run().add_picture(str(logos[0]), height=Cm(1.2))
        except Exception:  # pragma: no cover - un logo inválido no debe frenar el documento
            pass

    nombre = entidad.get("nombre_comercial") or entidad.get("razon_social")
    if nombre:
        corrida = encabezado.add_run(nombre)
        corrida.bold = True
        corrida.font.size = Pt(9)
        corrida.font.color.rgb = AZUL


def agregar_pie(seccion, payload: dict) -> None:
    """Pie con el título del documento y el número de página."""
    pie = seccion.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    corrida = pie.add_run(f"{payload.get('pie', '')} · Página ")
    corrida.font.size = Pt(8)
    corrida.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    campo_pagina(pie)


def render_bloques(documento: Document, payload: dict) -> None:
    """Traduce los bloques del payload a un documento de Word."""
    for bloque in payload.get("bloques", []):
        tipo = bloque.get("tipo")

        if tipo == "pagina":
            documento.add_page_break()

        elif tipo == "portada":
            for linea in bloque.get("lineas", []):
                parrafo = documento.add_paragraph()
                parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
                corrida = parrafo.add_run(linea.get("texto", ""))
                corrida.bold = bool(linea.get("negrita"))
                corrida.italic = bool(linea.get("cursiva"))
                if linea.get("tamano"):
                    corrida.font.size = Pt(linea["tamano"])

        elif tipo == "titulo":
            nivel = min(max(int(bloque.get("nivel", 1)), 1), 3)
            documento.add_heading(bloque.get("texto", ""), level=nivel)

        elif tipo == "parrafo":
            parrafo = documento.add_paragraph(bloque.get("texto", ""))
            if bloque.get("cursiva"):
                for corrida in parrafo.runs:
                    corrida.italic = True

        elif tipo in ("lista", "numerada"):
            numerada = tipo == "numerada" or bloque.get("numerada") is True
            estilo = "List Number" if numerada else "List Bullet"
            for item in bloque.get("items", []):
                documento.add_paragraph(item, style=estilo)

        elif tipo == "tabla":
            encabezado = bloque.get("encabezado", [])
            filas = bloque.get("filas", [])
            if not encabezado:
                continue
            tabla = documento.add_table(rows=1, cols=len(encabezado))
            tabla.style = "Table Grid"
            for indice, titulo in enumerate(encabezado):
                celda = tabla.rows[0].cells[indice]
                celda.text = str(titulo)
                sombrear(celda, AZUL_HEX)
                for corrida in celda.paragraphs[0].runs:
                    corrida.bold = True
            for indice, fila in enumerate(filas):
                celdas = tabla.add_row().cells
                for posicion, valor in enumerate(fila[: len(encabezado)]):
                    celdas[posicion].text = str(valor)
                    if indice % 2 == 1:
                        sombrear(celdas[posicion], GRIS_HEX)

        elif tipo == "indice":
            entradas = payload.get("indice", [])
            if not entradas:
                continue
            tabla = documento.add_table(rows=1, cols=2)
            tabla.style = "Table Grid"
            tabla.rows[0].cells[0].text = "Sección"
            tabla.rows[0].cells[1].text = "Página"
            for celda in tabla.rows[0].cells:
                sombrear(celda, AZUL_HEX)
                for corrida in celda.paragraphs[0].runs:
                    corrida.bold = True
            for entrada in entradas:
                celdas = tabla.add_row().cells
                celdas[0].text = str(entrada.get("texto", ""))
                celdas[1].text = str(entrada.get("pagina", ""))

        elif tipo == "firma":
            documento.add_paragraph("")
            documento.add_paragraph("")
            firma = documento.add_paragraph("_" * 40)
            firma.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cargo = documento.add_paragraph(bloque.get("cargo", ""))
            cargo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for corrida in cargo.runs:
                corrida.bold = True
            entidad = documento.add_paragraph(bloque.get("entidad", ""))
            entidad.alignment = WD_ALIGN_PARAGRAPH.CENTER
            documento.add_paragraph(bloque.get("texto", ""))

        else:
            raise SystemExit(f"bloque desconocido en el payload: {tipo}")


def verificar_sin_pendientes(documento: Document) -> None:
    """El generador no puede dejar un PENDIENTE en el documento final."""
    for parrafo in documento.paragraphs:
        if "PENDIENTE" in parrafo.text.upper():
            raise SystemExit(
                "el documento contiene un valor PENDIENTE: "
                f"{parrafo.text.strip()[:80]}"
            )
    for tabla in documento.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                if "PENDIENTE" in celda.text.upper():
                    raise SystemExit("el documento contiene un valor PENDIENTE en una tabla")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generador propio del usuario (ejemplo)")
    parser.add_argument("--entrada", required=True, help="payload JSON que entrega el motor")
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.entrada).read_text(encoding="utf-8"))

    documento = Document()
    seccion = documento.sections[0]
    seccion.top_margin = MARGEN
    seccion.bottom_margin = MARGEN
    seccion.left_margin = MARGEN
    seccion.right_margin = MARGEN

    aplicar_estilos(documento)
    agregar_membrete(seccion, payload)
    agregar_pie(seccion, payload)
    render_bloques(documento, payload)
    verificar_sin_pendientes(documento)

    salida = Path(payload["salida"])
    salida.parent.mkdir(parents=True, exist_ok=True)
    documento.save(salida)
    print(f"OK {salida} ({salida.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
