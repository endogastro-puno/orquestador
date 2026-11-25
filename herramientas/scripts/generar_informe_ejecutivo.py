#!/usr/bin/env python3
"""Genera el Informe Ejecutivo de Operaciones de AndesLogix S.A.C.

Demostración con datos ficticios aportados por el usuario. Usa python-docx.
La salida se resuelve con nuevo_entregable.resolver(): nunca sobrescribe.

Uso:
    python herramientas/scripts/generar_informe_ejecutivo.py [--salida RUTA]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nuevo_entregable import resolver  # noqa: E402

# Identidad visual definida por el usuario para este documento.
AZUL = RGBColor(0x1B, 0x36, 0x5D)
PIZARRA = RGBColor(0x4A, 0x55, 0x68)
CLARO = "F7FAFC"
FUENTE = "Calibri"

DATOS = {
    "razon_social": "AndesLogix S.A.C.",
    "ruc": "20609845123",
    "rubro": "Operador logístico y distribución farmacéutica regional",
    "sede": "Parque Industrial, Lote 14, Arequipa, Perú",
    "codigo": "INF-ADM-2026-042",
    "fecha": "25 de noviembre de 2026",
    "destinatario": "Ing. Valeria Mendoza",
    "cargo_destinatario": "Gerente General",
    "elaborador": "Lic. Carlos Paredes",
    "cargo_elaborador": "Jefatura de Administración y Operaciones",
    "titulo": "INFORME EJECUTIVO DE OPERACIONES Y PROPUESTA DE MEJORA ADMINISTRATIVA",
    "version": "1.0",
}

INDICADORES = [
    ("Tiempo promedio de despacho", "4.0 hrs", "5.2 hrs", "Crítico"),
    ("Exactitud de inventario (ERE)", "99.5%", "98.1%", "En observación"),
    ("Costo operativo por pedido", "S/ 18.50", "S/ 17.90", "Óptimo"),
    ("Incidencias de cadena de frío", "0", "2", "Crítico"),
]

INICIATIVAS = [
    ("Digitalización de guías de remisión", "Jefatura de Operaciones", 6, 8500.00),
    ("Control FEFO automatizado en almacén secundario", "Jefatura de Almacén", 8, 12000.00),
    ("Capacitación de flota en cadena de frío", "Jefatura de Transportes", 4, 4000.00),
]


def _fuente(run, tamano: float, color: RGBColor | None = None, negrita: bool = False) -> None:
    run.font.name = FUENTE
    run.font.size = Pt(tamano)
    run.bold = negrita
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for atributo in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{atributo}"), FUENTE)


def parrafo(
    documento: Document,
    texto: str,
    tamano: float = 10.5,
    color: RGBColor | None = None,
    negrita: bool = False,
    alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY,
    despues: int = 6,
):
    p = documento.add_paragraph()
    p.alignment = alineacion
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(despues)
    _fuente(p.add_run(texto), tamano, color, negrita)
    return p


def titulo(documento: Document, texto: str, tamano: float = 14, color: RGBColor = AZUL):
    p = documento.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.line_spacing = 1.15
    _fuente(p.add_run(texto), tamano, color, True)
    return p


def sombra(celda, color: str) -> None:
    tcpr = celda._tc.get_or_add_tcPr()
    shd = tcpr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcpr.append(shd)
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)


def sin_bordes(tabla) -> None:
    tblpr = tabla._tbl.tblPr
    borders = tblpr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tblpr.append(borders)
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        elemento = borders.find(qn(f"w:{lado}"))
        if elemento is None:
            elemento = OxmlElement(f"w:{lado}")
            borders.append(elemento)
        elemento.set(qn("w:val"), "nil")


def bordes_tabla(tabla, color: str = "CBD5E0") -> None:
    tblpr = tabla._tbl.tblPr
    borders = tblpr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tblpr.append(borders)
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        elemento = borders.find(qn(f"w:{lado}"))
        if elemento is None:
            elemento = OxmlElement(f"w:{lado}")
            borders.append(elemento)
        elemento.set(qn("w:val"), "single")
        elemento.set(qn("w:sz"), "4")
        elemento.set(qn("w:color"), color)


def celda_texto(celda, texto: str, negrita: bool = False, alineacion=None, color=None) -> None:
    celda.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = celda.paragraphs[0]
    p.alignment = alineacion or WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(0)
    _fuente(p.add_run(texto), 10.5, color, negrita)


def cabecera_repetida(fila) -> None:
    trpr = fila._tr.get_or_add_trPr()
    encabezado = OxmlElement("w:tblHeader")
    encabezado.set(qn("w:val"), "true")
    trpr.append(encabezado)


def no_dividir(fila) -> None:
    """Evita que una fila se rompa entre páginas y deje palabras huérfanas."""
    trpr = fila._tr.get_or_add_trPr()
    if trpr.find(qn("w:cantSplit")) is None:
        trpr.append(OxmlElement("w:cantSplit"))


def campo(p, codigo: str) -> None:
    run = p.add_run()
    inicio = OxmlElement("w:fldChar")
    inicio.set(qn("w:fldCharType"), "begin")
    instruccion = OxmlElement("w:instrText")
    instruccion.set(qn("xml:space"), "preserve")
    instruccion.text = codigo
    separador = OxmlElement("w:fldChar")
    separador.set(qn("w:fldCharType"), "separate")
    texto = OxmlElement("w:t")
    texto.text = "1"
    fin = OxmlElement("w:fldChar")
    fin.set(qn("w:fldCharType"), "end")
    for elemento in (inicio, instruccion, separador, texto, fin):
        run._r.append(elemento)
    _fuente(run, 9, PIZARRA)


def configurar(documento: Document) -> None:
    seccion = documento.sections[0]
    seccion.top_margin = Cm(2.5)
    seccion.bottom_margin = Cm(2.5)
    seccion.left_margin = Cm(2.5)
    seccion.right_margin = Cm(2.5)

    normal = documento.styles["Normal"]
    normal.font.name = FUENTE
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = Pt(6)

    # El estilo "Header" trae tabulaciones de centro en pulgadas que ganan a
    # cualquier tabulación nueva. Una tabla sin bordes es determinista: nombre
    # a la izquierda y código a la derecha, sin depender de estilos ocultos.
    cabecera = seccion.header
    for parrafo_viejo in list(cabecera.paragraphs):
        parrafo_viejo._element.getparent().remove(parrafo_viejo._element)
    tabla = cabecera.add_table(rows=1, cols=2, width=Cm(16))
    tabla.autofit = False
    sin_bordes(tabla)
    for indice, texto in enumerate((DATOS["razon_social"], DATOS["codigo"])):
        celda = tabla.rows[0].cells[indice]
        celda.width = Cm(8)
        tabla.columns[indice].width = Cm(8)
        parrafo_celda = celda.paragraphs[0]
        parrafo_celda.paragraph_format.space_after = Pt(0)
        parrafo_celda.paragraph_format.line_spacing = 1.15
        parrafo_celda.alignment = (
            WD_ALIGN_PARAGRAPH.LEFT if indice == 0 else WD_ALIGN_PARAGRAPH.RIGHT
        )
        _fuente(parrafo_celda.add_run(texto), 9, PIZARRA)

    pie = seccion.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pie.paragraph_format.space_after = Pt(0)
    _fuente(pie.add_run("Página "), 9, PIZARRA)
    campo(pie, "PAGE")
    _fuente(pie.add_run(" de "), 9, PIZARRA)
    campo(pie, "NUMPAGES")

    confidencial = seccion.footer.add_paragraph()
    confidencial.alignment = WD_ALIGN_PARAGRAPH.CENTER
    confidencial.paragraph_format.space_after = Pt(0)
    _fuente(
        confidencial.add_run("Documento confidencial — uso interno exclusivo"),
        8,
        PIZARRA,
    )


def portada(documento: Document) -> None:
    parrafo(documento, "", despues=24)
    parrafo(documento, DATOS["razon_social"], 20, AZUL, True, WD_ALIGN_PARAGRAPH.CENTER, 4)
    parrafo(documento, DATOS["ruc"], 11, PIZARRA, False, WD_ALIGN_PARAGRAPH.CENTER, 4)
    parrafo(documento, DATOS["rubro"], 11, PIZARRA, False, WD_ALIGN_PARAGRAPH.CENTER, 4)
    parrafo(documento, DATOS["sede"], 11, PIZARRA, False, WD_ALIGN_PARAGRAPH.CENTER, 28)
    parrafo(documento, DATOS["titulo"], 20, AZUL, True, WD_ALIGN_PARAGRAPH.CENTER, 12)
    parrafo(documento, DATOS["codigo"], 12, PIZARRA, False, WD_ALIGN_PARAGRAPH.CENTER, 4)
    parrafo(documento, DATOS["fecha"], 12, PIZARRA, False, WD_ALIGN_PARAGRAPH.CENTER, 24)
    parrafo(
        documento,
        "DIRIGIDO A: " + DATOS["destinatario"] + " — " + DATOS["cargo_destinatario"],
        11,
        AZUL,
        True,
        WD_ALIGN_PARAGRAPH.CENTER,
        4,
    )
    parrafo(
        documento,
        "ELABORADO POR: " + DATOS["elaborador"] + " — " + DATOS["cargo_elaborador"],
        11,
        AZUL,
        True,
        WD_ALIGN_PARAGRAPH.CENTER,
        24,
    )

    titulo(documento, "Control de versiones", 12)
    tabla = documento.add_table(rows=2, cols=4)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.autofit = False
    anchos = [Cm(2.5), Cm(4.0), Cm(4.5), Cm(5.0)]
    cabeceras = ["Versión", "Fecha", "Elaborado por", "Estado"]
    filas = [
        ["1.0", DATOS["fecha"], DATOS["elaborador"], "Aprobación"],
    ]
    for i, ancho in enumerate(anchos):
        tabla.columns[i].width = ancho
    for i, texto in enumerate(cabeceras):
        celda = tabla.rows[0].cells[i]
        celda.width = anchos[i]
        sombra(celda, "1B365D")
        celda_texto(celda, texto, True, WD_ALIGN_PARAGRAPH.CENTER, RGBColor(255, 255, 255))
    cabecera_repetida(tabla.rows[0])
    for j, fila in enumerate(filas):
        for i, texto in enumerate(fila):
            celda = tabla.rows[j + 1].cells[i]
            celda.width = anchos[i]
            if j % 2 == 1:
                sombra(celda, CLARO)
            celda_texto(celda, texto)
    bordes_tabla(tabla)


def resumen(documento: Document) -> None:
    titulo(documento, "Resumen ejecutivo")
    parrafo(
        documento,
        "Durante el último trimestre, AndesLogix S.A.C. mantuvo la continuidad de la "
        "distribución farmacéutica regional y logró contener el costo operativo por pedido "
        "por debajo de la meta prevista (S/ 17.90 frente a S/ 18.50). Sin embargo, el "
        "desempeño del despacho se deterioró: el tiempo promedio ascendió a 5.2 horas "
        "frente a una meta de 4.0, y se registraron dos incidencias de cadena de frío en "
        "el almacén secundario. Ambos resultados concentran la atención de esta gestión.",
    )
    parrafo(
        documento,
        "El objetivo de este informe es proponer un plan de acción que reduzca los tiempos "
        "de despacho en un 22% en un horizonte de ocho semanas, sin incrementar el costo "
        "unitario ni comprometer la trazabilidad térmica. La propuesta prioriza la "
        "digitalización de guías, el control FEFO automatizado y la capacitación de flota, "
        "con un presupuesto total estimado de S/ 24,500.00.",
    )


def tabla_datos(
    documento: Document,
    cabeceras: list[str],
    filas: list[list[str]],
    anchos: list[float],
    columnas_numericas: set[int],
) -> None:
    tabla = documento.add_table(rows=1 + len(filas), cols=len(cabeceras))
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.autofit = False
    for i, ancho in enumerate(anchos):
        tabla.columns[i].width = Cm(ancho)
    for i, texto in enumerate(cabeceras):
        celda = tabla.rows[0].cells[i]
        celda.width = Cm(anchos[i])
        sombra(celda, "1B365D")
        alineacion = WD_ALIGN_PARAGRAPH.RIGHT if i in columnas_numericas else WD_ALIGN_PARAGRAPH.LEFT
        celda_texto(celda, texto, True, alineacion, RGBColor(255, 255, 255))
    cabecera_repetida(tabla.rows[0])
    for j, fila in enumerate(filas):
        no_dividir(tabla.rows[j + 1])
        for i, texto in enumerate(fila):
            celda = tabla.rows[j + 1].cells[i]
            celda.width = Cm(anchos[i])
            if j % 2 == 1:
                sombra(celda, CLARO)
            alineacion = WD_ALIGN_PARAGRAPH.RIGHT if i in columnas_numericas else WD_ALIGN_PARAGRAPH.LEFT
            critico = texto in ("Crítico",)
            celda_texto(celda, texto, critico, alineacion, AZUL if critico else None)
    bordes_tabla(tabla)


def indicadores(documento: Document) -> None:
    titulo(documento, "Indicadores clave de gestión")
    parrafo(
        documento,
        "Cuadro comparativo del trimestre. El estado se evalúa contra la meta aprobada "
        "por Gerencia General.",
    )
    tabla_datos(
        documento,
        ["Indicador", "Meta", "Actual", "Estado"],
        [list(fila) for fila in INDICADORES],
        [6.5, 3.0, 3.0, 3.5],
        {1, 2},
    )


def diagnostico(documento: Document) -> None:
    titulo(documento, "Diagnóstico de cuellos de botella")
    problemas = [
        (
            "Recepción manual de guías de remisión",
            "La digitación manual en el punto de recepción genera reprocesos y retrasa la "
            "disponibilidad del pedido. Es la causa principal del desvío de 1.2 horas en el "
            "tiempo de despacho.",
        ),
        (
            "Ausencia de alertas FEFO en almacén secundario",
            "El control de vencimientos se realiza de forma visual y periódica. Sin alertas "
            "tempranas, el inventario próximo al vencimiento no se reubica a tiempo, lo que explica "
            "las dos incidencias de cadena de frío.",
        ),
        (
            "Retrasos en la liquidación de transportistas",
            "La liquidación se concentra al cierre del mes y depende de documentación física. "
            "El retraso afecta la visibilidad del costo real por pedido y dificulta la "
            "corrección oportuna de desvíos.",
        ),
    ]
    for indice, (nombre, detalle) in enumerate(problemas, start=1):
        p = documento.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        _fuente(p.add_run(f"{indice}. "), 10.5, AZUL, True)
        _fuente(p.add_run(nombre + ". "), 10.5, AZUL, True)
        _fuente(p.add_run(detalle), 10.5)


def plan_y_presupuesto(documento: Document) -> None:
    titulo(documento, "Plan de acción y presupuesto estimado")
    parrafo(
        documento,
        "Las tres iniciativas se ejecutan en secuencia y comparten el mismo cronograma "
        "de control semanal. El presupuesto total asciende a S/ 24,500.00.",
    )
    filas = [
        [nombre, responsable, f"{semanas} semanas", f"S/ {monto:,.2f}"]
        for nombre, responsable, semanas, monto in INICIATIVAS
    ]
    total = sum(item[3] for item in INICIATIVAS)
    filas.append(["TOTAL", "", "", f"S/ {total:,.2f}"])
    tabla_datos(
        documento,
        ["Iniciativa", "Responsable", "Plazo", "Presupuesto"],
        filas,
        [6.0, 3.8, 2.6, 3.6],
        {2, 3},
    )

    titulo(documento, "Cronograma", 12)
    hitos = [
        "Semanas 1 a 2 — levantamiento de procesos y parametrización inicial.",
        "Semanas 3 a 6 — digitalización de guías y capacitación de flota.",
        "Semanas 5 a 8 — implementación del control FEFO automatizado.",
        "Semana 8 — medición del tiempo de despacho y cierre del informe de resultados.",
    ]
    for hito in hitos:
        parrafo(documento, "•  " + hito, 10.5, None, False, WD_ALIGN_PARAGRAPH.LEFT, 3)


def firmas(documento: Document) -> None:
    titulo(documento, "Firmas y aprobación")
    parrafo(documento, "", despues=10)
    tabla = documento.add_table(rows=3, cols=2)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.autofit = False
    for i in range(2):
        tabla.columns[i].width = Cm(8.0)
        for fila in tabla.rows:
            fila.cells[i].width = Cm(8.0)
    celda_texto(tabla.rows[0].cells[0], "Elaborado por", True, WD_ALIGN_PARAGRAPH.CENTER, AZUL)
    celda_texto(tabla.rows[0].cells[1], "Aprobado por", True, WD_ALIGN_PARAGRAPH.CENTER, AZUL)
    celda_texto(tabla.rows[1].cells[0], "______________________________________", False, WD_ALIGN_PARAGRAPH.CENTER)
    celda_texto(tabla.rows[1].cells[1], "______________________________________", False, WD_ALIGN_PARAGRAPH.CENTER)
    celda_texto(tabla.rows[2].cells[0], DATOS["elaborador"], True, WD_ALIGN_PARAGRAPH.CENTER)
    celda_texto(tabla.rows[2].cells[1], DATOS["destinatario"], True, WD_ALIGN_PARAGRAPH.CENTER)
    parrafo(
        documento,
        DATOS["cargo_elaborador"] + "     |     " + DATOS["cargo_destinatario"],
        9,
        PIZARRA,
        False,
        WD_ALIGN_PARAGRAPH.CENTER,
        2,
    )


def generar(salida: Path) -> Path:
    documento = Document()
    configurar(documento)
    portada(documento)
    documento.add_page_break()
    resumen(documento)
    indicadores(documento)
    diagnostico(documento)
    documento.add_page_break()
    plan_y_presupuesto(documento)
    documento.add_page_break()
    firmas(documento)
    salida.parent.mkdir(parents=True, exist_ok=True)
    documento.save(salida)
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--salida", help="ruta explícita; si existe, se rechaza sin sobrescribir")
    args = parser.parse_args()
    if args.salida:
        destino = Path(args.salida).resolve()
        if destino.exists():
            print(f"ERROR: ya existe {destino}. No se sobrescribe.", file=sys.stderr)
            return 1
    else:
        destino = resolver(
            "word", "Informe Ejecutivo de Operaciones AndesLogix", "2026-11-25"
        )
    generar(destino)
    print(f"OK {destino.relative_to(RAIZ).as_posix()} ({destino.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
