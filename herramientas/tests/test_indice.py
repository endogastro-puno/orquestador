"""Regresiones del índice de documentos: indexar y buscar.

Sólo biblioteca estándar, salvo la prueba del PDF escaneado, que se salta si
falta `reportlab`.

    python -m unittest discover -s herramientas/tests -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_SCRIPTS = RAIZ / "herramientas" / "scripts"
sys.path.insert(0, str(DIR_SCRIPTS))

import buscar_documentos as bd  # noqa: E402
import indexar_documentos as ix  # noqa: E402
import menu  # noqa: E402

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


def escribir_docx(destino: Path, texto: str) -> Path:
    """Arma un .docx mínimo con un párrafo dado."""
    documento = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        f"  <w:body><w:p><w:r><w:t>{texto}</w:t></w:r></w:p></w:body>\n"
        "</w:document>"
    )
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as paquete:
        paquete.writestr("[Content_Types].xml", TIPOS_DOC)
        paquete.writestr("_rels/.rels", RELS_DOC)
        paquete.writestr("word/document.xml", documento)
    return destino


class SelvaDeCarpetas(unittest.TestCase):
    """Un árbol de carpetas con documentos variados, como el del usuario final."""

    def setUp(self) -> None:
        import os

        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.addCleanup(self.temporal.cleanup)

        self.raiz = self.base / "FOLDER-PRINCIPAL"
        (self.raiz / "FOLDER 1" / "sub").mkdir(parents=True)
        (self.raiz / "FOLDER 2").mkdir()
        self.contrato = escribir_docx(
            self.raiz / "FOLDER 1" / "contrato-acme.docx", "Cotización de servicios de mantenimiento ACME"
        )
        (self.raiz / "FOLDER 1" / "sub" / "carta.txt").write_text(
            "Carta de presentación con cláusula de confidencialidad.", encoding="utf-8"
        )
        (self.raiz / "FOLDER 2" / "tarifas.csv").write_text("codigo,precio\nS-001,50\n", encoding="utf-8")
        (self.raiz / "FOLDER 2" / "falso.docx").write_bytes(b"esto no es un zip")
        (self.raiz / "sueltos.md").write_text("# Nota\n\nreunión del viernes", encoding="utf-8")
        (self.raiz / "binario.exe").write_bytes(b"no es un documento")
        (self.raiz / ".git").mkdir()
        (self.raiz / ".git" / "config").write_text("x", encoding="utf-8")
        self.raiz.joinpath("~$temporal.docx").write_text("lock de Office", encoding="utf-8")
        # Fechas distintas para que el incremental las distinga.
        for indice, ruta in enumerate(self.raiz.rglob("*")):
            if ruta.is_file():
                os.utime(ruta, (1_600_000_000 + indice, 1_600_000_000 + indice))

        self.espacio = self.base / "espacio"


class TestIndexar(SelvaDeCarpetas):
    def test_indexa_documentos_y_guarda_en_indice(self) -> None:
        resumen = ix.indexar(self.raiz, self.espacio)

        self.assertEqual(resumen["nuevos"], 5)  # 4 documentos + 1 corrupto
        self.assertEqual(resumen["errores"], 1)
        destino = Path(resumen["indice"])
        self.assertTrue(destino.is_file())
        self.assertEqual(destino.parent, self.espacio / "indice")

        indice = ix.cargar(destino)
        rutas = {entrada["ruta"] for entrada in indice["archivos"]}
        self.assertIn("FOLDER 1/contrato-acme.docx", rutas)
        self.assertIn("FOLDER 2/tarifas.csv", rutas)
        self.assertIn("sueltos.md", rutas)
        self.assertNotIn("binario.exe", rutas)  # sin --todo no entra
        self.assertNotIn(".git/config", rutas)  # carpeta excluida
        self.assertFalse(any(ruta.startswith("~$") for ruta in rutas))  # lock de Office

    def test_el_corrupto_queda_en_el_mapa_con_su_error(self) -> None:
        resumen = ix.indexar(self.raiz, self.espacio)

        indice = ix.cargar(Path(resumen["indice"]))
        corrupto = {entrada["ruta"]: entrada for entrada in indice["archivos"]}["FOLDER 2/falso.docx"]
        self.assertTrue(corrupto["documento"])
        self.assertIsNotNone(corrupto["error"])
        self.assertIsNone(corrupto["texto"])

    def test_texto_guardado_por_defecto(self) -> None:
        resumen = ix.indexar(self.raiz, self.espacio)

        indice = ix.cargar(Path(resumen["indice"]))
        por_ruta = {entrada["ruta"]: entrada for entrada in indice["archivos"]}
        self.assertIn("Cotización de servicios", por_ruta["FOLDER 1/contrato-acme.docx"]["texto"])
        self.assertIsNone(por_ruta["FOLDER 2/falso.docx"]["texto"])

    def test_incremental_no_relee_lo_que_no_cambio(self) -> None:
        ix.indexar(self.raiz, self.espacio)

        resumen = ix.indexar(self.raiz, self.espacio)

        self.assertEqual(resumen["nuevos"], 0)
        self.assertEqual(resumen["cambiados"], 0)
        self.assertEqual(resumen["reutilizados"], 5)

    def test_cambiado_se_relee(self) -> None:
        import os

        ix.indexar(self.raiz, self.espacio)
        carta = self.raiz / "FOLDER 1" / "sub" / "carta.txt"
        carta.write_text("Carta actualizada con más contenido.", encoding="utf-8")
        os.utime(carta, (1_700_000_000, 1_700_000_000))

        resumen = ix.indexar(self.raiz, self.espacio)

        self.assertEqual(resumen["cambiados"], 1)
        self.assertEqual(resumen["reutilizados"], 4)
        indice = ix.cargar(Path(resumen["indice"]))
        por_ruta = {entrada["ruta"]: entrada for entrada in indice["archivos"]}
        self.assertIn("actualizada", por_ruta["FOLDER 1/sub/carta.txt"]["texto"])

    def test_sin_texto(self) -> None:
        resumen = ix.indexar(self.raiz, self.espacio, con_texto=False)

        indice = ix.cargar(Path(resumen["indice"]))
        self.assertFalse(indice["con_texto"])
        for entrada in indice["archivos"]:
            if entrada["documento"]:
                self.assertIsNone(entrada["texto"])

    def test_todo_incluye_no_documentos(self) -> None:
        resumen = ix.indexar(self.raiz, self.espacio, todo=True)

        indice = ix.cargar(Path(resumen["indice"]))
        rutas = {entrada["ruta"] for entrada in indice["archivos"]}
        self.assertIn("binario.exe", rutas)

    def test_cli_exito_y_json(self) -> None:
        with redirect_stdout(io.StringIO()):
            codigo = ix.main(["--ruta", str(self.raiz), "--workspace", str(self.espacio), "--json"])
        self.assertEqual(codigo, 0)

        salida = io.StringIO()
        with redirect_stdout(salida):
            ix.main(["--ruta", str(self.raiz), "--workspace", str(self.espacio), "--json"])
        resumen = json.loads(salida.getvalue())
        self.assertEqual(resumen["total"], 5)

    def test_cli_ruta_inexistente(self) -> None:
        with redirect_stderr(io.StringIO()):
            codigo = ix.main(["--ruta", str(self.base / "no-hay"), "--workspace", str(self.espacio)])
        self.assertEqual(codigo, 1)

    def test_selftest(self) -> None:
        self.assertEqual(ix.selftest(), 0)


class TestBuscar(SelvaDeCarpetas):
    def setUp(self) -> None:
        super().setUp()
        ix.indexar(self.raiz, self.espacio)
        self.indices = bd.cargar_indices(self.espacio)

    def test_busca_en_nombre_sin_tildes(self) -> None:
        resultados, total = bd.buscar(self.indices, consulta="contrato")

        self.assertEqual(total, 1)
        self.assertEqual(resultados[0]["ruta"], "FOLDER 1/contrato-acme.docx")
        self.assertEqual(resultados[0]["donde"], "nombre")

    def test_busca_en_el_texto_con_snippet(self) -> None:
        resultados, _ = bd.buscar(self.indices, consulta="confidencialidad")

        self.assertEqual(resultados[0]["ruta"], "FOLDER 1/sub/carta.txt")
        self.assertEqual(resultados[0]["donde"], "texto")
        self.assertIn("confidencialidad", resultados[0]["snippet"])

    def test_busca_dentro_de_un_docx(self) -> None:
        resultados, _ = bd.buscar(self.indices, consulta="mantenimiento")

        self.assertEqual(resultados[0]["ruta"], "FOLDER 1/contrato-acme.docx")

    def test_filtro_por_tipo(self) -> None:
        resultados, _ = bd.buscar(self.indices, tipos=("csv",))

        self.assertEqual({resultado["ruta"] for resultado in resultados}, {"FOLDER 2/tarifas.csv"})

    def test_filtro_por_carpeta(self) -> None:
        resultados, _ = bd.buscar(self.indices, carpeta="folder 2", consulta="")

        rutas = {resultado["ruta"] for resultado in resultados}
        self.assertIn("FOLDER 2/tarifas.csv", rutas)
        self.assertIn("FOLDER 2/falso.docx", rutas)
        self.assertNotIn("FOLDER 1/contrato-acme.docx", rutas)

    def test_solo_nombres(self) -> None:
        resultados, _ = bd.buscar(self.indices, consulta="reunion", solo_nombres=True)

        self.assertEqual(resultados, [])

    def test_sin_resultados(self) -> None:
        resultados, total = bd.buscar(self.indices, consulta="inexistente-total")
        self.assertEqual((resultados, total), ([], 0))

    def test_maximo_recorta(self) -> None:
        resultados, total = bd.buscar(self.indices, consulta="", tipos=("txt", "md", "csv", "docx"), maximo=2)

        self.assertEqual(len(resultados), 2)
        self.assertEqual(total, 5)

    def test_cli_sin_indice_ayuda(self) -> None:
        error = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(error):
            codigo = bd.main(["algo", "--workspace", str(self.base / "espacio-vacio")])

        self.assertEqual(codigo, 1)
        self.assertIn("indexar_documentos.py", error.getvalue())

    def test_cli_json(self) -> None:
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = bd.main(["contrato", "--workspace", str(self.espacio), "--json"])

        self.assertEqual(codigo, 0)
        payload = json.loads(salida.getvalue())
        self.assertEqual(payload["total"], 1)

    def test_cli_sin_consulta_ni_filtro(self) -> None:
        error = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(error):
            codigo = bd.main(["--workspace", str(self.espacio)])

        self.assertEqual(codigo, 1)
        self.assertIn("nada que buscar", error.getvalue())

    def test_cli_resultado_humano(self) -> None:
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = bd.main(["confidencialidad", "--workspace", str(self.espacio)])

        self.assertEqual(codigo, 0)
        texto = salida.getvalue()
        self.assertIn("FOLDER 1/sub/carta.txt", texto)
        self.assertIn("texto:", texto)

    def test_selftest(self) -> None:
        self.assertEqual(bd.selftest(), 0)


@unittest.skipUnless(
    __import__("importlib").util.find_spec("reportlab") is not None, "falta reportlab"
)
class TestPdfEscaneado(SelvaDeCarpetas):
    def _pdf_sin_texto(self) -> Path:
        from reportlab.pdfgen import canvas

        ruta = self.raiz / "FOLDER 2" / "escaneado.pdf"
        lienzo = canvas.Canvas(str(ruta))
        lienzo.showPage()  # página vacía: simula un PDF escaneado
        lienzo.save()
        return ruta

    def test_el_escaneado_queda_marcado_y_se_encuentra(self) -> None:
        self._pdf_sin_texto()
        resumen = ix.indexar(self.raiz, self.espacio)

        self.assertEqual(resumen["escaneados"], 1)
        resultados, total = bd.buscar(bd.cargar_indices(self.espacio), escaneados=True)
        self.assertEqual(total, 1)
        self.assertEqual(resultados[0]["ruta"], "FOLDER 2/escaneado.pdf")
        self.assertTrue(resultados[0]["escaneado"])


class TestMenuIndice(unittest.TestCase):
    def test_el_menu_ofrece_indexar_y_buscar(self) -> None:
        por_numero = {accion["numero"]: accion for accion in menu.ACCIONES}
        self.assertEqual(por_numero[12]["script"], "indexar_documentos.py")
        self.assertEqual(por_numero[13]["script"], "buscar_documentos.py")
        self.assertIn("pide_carpeta", menu.PIDE)
        self.assertIn("pide_busqueda", menu.PIDE)

    def test_selftest_del_menu(self) -> None:
        self.assertEqual(menu.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
