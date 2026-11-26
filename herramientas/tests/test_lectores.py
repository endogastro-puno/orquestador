"""Regresiones de los lectores de documentos y de la prueba de humo.

Sólo biblioteca estándar, salvo las pruebas de PDF y Excel: ésas se saltean si
la dependencia del formato no está instalada.

    python -m unittest discover -s herramientas/tests -v
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "herramientas" / "scripts"))

import leer_documento as lector  # noqa: E402
import selftest  # noqa: E402

TIPOS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

DOCUMENTO = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Primer párrafo</w:t></w:r></w:p>
    <w:p><w:r><w:t>Segundo</w:t><w:tab/><w:t>con tabulación</w:t></w:r></w:p>
    <w:p/>
    <w:tbl>
      <w:tr><w:tc><w:p><w:r><w:t>Código</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Monto</w:t></w:r></w:p></w:tc></w:tr>
      <w:tr><w:tc><w:p><w:r><w:t>P-001</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>10.00</w:t></w:r></w:p></w:tc></w:tr>
    </w:tbl>
  </w:body>
</w:document>"""

NUCLEO = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties
    xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/">
  <dc:title>Informe de prueba</dc:title>
  <dc:creator>ACME</dc:creator>
  <dcterms:created>2026-11-25T10:00:00Z</dcterms:created>
</cp:coreProperties>"""


def escribir_docx(destino: Path) -> Path:
    """Arma un .docx mínimo con las cuatro partes que importan."""
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as paquete:
        paquete.writestr("[Content_Types].xml", TIPOS)
        paquete.writestr("_rels/.rels", RELS)
        paquete.writestr("word/document.xml", DOCUMENTO)
        paquete.writestr("docProps/core.xml", NUCLEO)
    return destino


class BaseTemporal(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.addCleanup(self.temporal.cleanup)


class TestDocx(BaseTemporal):
    def test_lee_parrafos_y_tabulaciones(self) -> None:
        ruta = escribir_docx(self.base / "x.docx")

        resultado = lector.leer(ruta)

        self.assertEqual(resultado["parrafos"][0], "Primer párrafo")
        self.assertIn("Segundo\tcon tabulación", resultado["parrafos"])
        self.assertEqual(len(resultado["parrafos"]), 2)

    def test_lee_tablas(self) -> None:
        ruta = escribir_docx(self.base / "x.docx")

        resultado = lector.leer(ruta)

        self.assertEqual(len(resultado["tablas"]), 1)
        self.assertEqual(resultado["tablas"][0][1], ["P-001", "10.00"])

    def test_lee_metadatos(self) -> None:
        ruta = escribir_docx(self.base / "x.docx")

        resultado = lector.leer(ruta)

        self.assertEqual(resultado["metadatos"]["titulo"], "Informe de prueba")
        self.assertEqual(resultado["metadatos"]["autor"], "ACME")

    def test_contrato_de_salida_completo(self) -> None:
        ruta = escribir_docx(self.base / "x.docx")

        resultado = lector.leer(ruta)

        for clave in ("ok", "formato", "ruta", "bytes", "metadatos", "texto", "parrafos", "tablas"):
            self.assertIn(clave, resultado)
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["formato"], "docx")
        self.assertGreater(resultado["bytes"], 0)
        self.assertNotIn("C:\\", resultado["ruta"])

    def test_un_zip_que_no_es_docx_falla(self) -> None:
        ruta = self.base / "falso.docx"
        with zipfile.ZipFile(ruta, "w") as paquete:
            paquete.writestr("cualquier-cosa.txt", "no es word")

        with self.assertRaises((KeyError, zipfile.BadZipFile)):
            lector.leer(ruta)


class TestTextosPlanos(BaseTemporal):
    def test_markdown(self) -> None:
        ruta = self.base / "nota.md"
        ruta.write_text("# Título\n\nCuerpo.\n", encoding="utf-8")

        resultado = lector.leer(ruta)

        self.assertEqual(resultado["formato"], "md")
        self.assertIn("Cuerpo.", resultado["texto"])

    def test_csv_con_bom(self) -> None:
        ruta = self.base / "entidad.csv"
        ruta.write_text("\ufeffclave,valor\nrazon_social,ACME S.A.C.\n", encoding="utf-8")

        resultado = lector.leer(ruta)

        self.assertEqual(resultado["filas"][0], ["clave", "valor"])
        self.assertEqual(resultado["filas"][1][1], "ACME S.A.C.")

    def test_txt(self) -> None:
        ruta = self.base / "nota.txt"
        ruta.write_text("hola", encoding="utf-8")

        self.assertEqual(lector.leer(ruta)["texto"], "hola")


class TestErrores(unittest.TestCase):
    def test_formato_no_soportado_lista_los_validos(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "x.pptx"
            ruta.write_text("x", encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                lector.leer(ruta)

            self.assertIn(".docx", str(ctx.exception))
            self.assertIn(".pdf", str(ctx.exception))

    def test_archivo_inexistente(self) -> None:
        with self.assertRaises(ValueError):
            lector.leer(Path("no-existe.docx"))

    def test_la_cli_reporta_error_en_json(self) -> None:
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = lector.main(["no-existe.pdf", "--json"])

        self.assertEqual(codigo, 1)
        self.assertFalse(json.loads(salida.getvalue())["ok"])


class TestCliLectura(BaseTemporal):
    def test_json_con_recorte_de_texto(self) -> None:
        ruta = self.base / "nota.txt"
        ruta.write_text("x" * 100, encoding="utf-8")
        salida = io.StringIO()

        with contextlib.redirect_stdout(salida):
            codigo = lector.main([str(ruta), "--json", "--max-caracteres", "10"])

        payload = json.loads(salida.getvalue())
        self.assertEqual(codigo, 0)
        self.assertEqual(len(payload["texto"]), 10)
        self.assertTrue(payload["truncado"])

    def test_texto_plano_sin_metadatos(self) -> None:
        ruta = self.base / "nota.md"
        ruta.write_text("contenido", encoding="utf-8")
        salida = io.StringIO()

        with contextlib.redirect_stdout(salida):
            codigo = lector.main([str(ruta), "--texto"])

        self.assertEqual(codigo, 0)
        self.assertEqual(salida.getvalue().strip(), "contenido")

    def test_texto_plano_respeta_max_caracteres(self) -> None:
        ruta = self.base / "nota.txt"
        ruta.write_text("x" * 100, encoding="utf-8")
        salida = io.StringIO()

        with contextlib.redirect_stdout(salida):
            codigo = lector.main([str(ruta), "--texto", "--max-caracteres", "7"])

        self.assertEqual(codigo, 0)
        self.assertEqual(salida.getvalue().strip(), "x" * 7)


@unittest.skipUnless(
    __import__("importlib").util.find_spec("openpyxl") is not None, "falta openpyxl"
)
class TestXlsx(BaseTemporal):
    def test_lee_hojas_y_filas(self) -> None:
        import openpyxl

        ruta = self.base / "planilla.xlsx"
        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja.title = "Tarifas"
        hoja.append(["servicio", "precio"])
        hoja.append(["consulta", 50])
        libro.save(ruta)

        resultado = lector.leer(ruta)

        self.assertEqual(resultado["hojas"][0]["nombre"], "Tarifas")
        self.assertEqual(resultado["hojas"][0]["filas"][1], ["consulta", "50"])


@unittest.skipUnless(
    __import__("importlib").util.find_spec("reportlab") is not None, "falta reportlab"
)
class TestPdf(BaseTemporal):
    def test_lee_paginas(self) -> None:
        from reportlab.pdfgen import canvas

        ruta = self.base / "contrato.pdf"
        lienzo = canvas.Canvas(str(ruta))
        lienzo.drawString(72, 720, "Contrato de prueba")
        lienzo.showPage()
        lienzo.save()

        resultado = lector.leer(ruta)

        self.assertEqual(resultado["formato"], "pdf")
        self.assertEqual(len(resultado["paginas"]), 1)
        self.assertIn("Contrato de prueba", resultado["paginas"][0]["texto"])


@unittest.skipUnless(
    __import__("importlib").util.find_spec("reportlab") is not None, "falta reportlab"
)
class TestPdfSinTexto(BaseTemporal):
    def _pdf_vacio(self) -> Path:
        from reportlab.pdfgen import canvas

        ruta = self.base / "escaneado.pdf"
        lienzo = canvas.Canvas(str(ruta))
        lienzo.showPage()  # página sin texto: simula un escaneo
        lienzo.save()
        return ruta

    def test_avisa_y_sale_con_codigo_2_en_json(self) -> None:
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(io.StringIO()):
            codigo = lector.main([str(self._pdf_vacio()), "--json"])

        payload = json.loads(salida.getvalue())
        self.assertEqual(codigo, 2)
        self.assertIn("escaneado", payload["aviso"])

    def test_avisa_en_modo_humano_y_en_texto(self) -> None:
        for extra in ([], ["--texto"]):
            with self.subTest(extra=extra):
                error = io.StringIO()
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
                    codigo = lector.main([str(self._pdf_vacio()), *extra])

                self.assertEqual(codigo, 2)
                self.assertIn("AVISO", error.getvalue())


class TestSelftest(unittest.TestCase):
    def test_la_prueba_de_humo_pasa(self) -> None:
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = selftest.main(["--json"])

        payload = json.loads(salida.getvalue())
        estados = {resultado["camino"]: resultado["estado"] for resultado in payload["resultados"]}

        self.assertEqual(codigo, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(estados["generador-usuario"], "OK")
        self.assertNotIn("FALLA", estados.values())
