"""Regresiones del OCR de escaneados y su integración con el índice.

La cadena OCR real (Tesseract + Poppler) no está en CI: `pytesseract`,
`pdf2image`, `PIL` y los binarios se sustituyen con fakes en `sys.modules`
y `shutil.which`. Así se prueba la lógica sin instalar nada.

    python -m unittest discover -s herramientas/tests -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
DIR_SCRIPTS = RAIZ / "herramientas" / "scripts"
sys.path.insert(0, str(DIR_SCRIPTS))

import buscar_documentos as bd  # noqa: E402
import indexar_documentos as ix  # noqa: E402
import instalar_todo as inst  # noqa: E402
import menu  # noqa: E402
import ocr_documento as ocr  # noqa: E402


class _TesseractNotFoundErrorFake(Exception):
    pass


class _FakeImagen:
    def __init__(self, nombre="pagina"):
        self.nombre = nombre
        self.width = 100
        self.height = 100

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _modulos_fakes() -> dict:
    """Cadena OCR falsa como módulos reales en un dict para `sys.modules`."""
    import types

    fake_pytesseract = types.ModuleType("pytesseract")
    fake_pytesseract.TesseractNotFoundError = _TesseractNotFoundErrorFake  # type: ignore[attr-defined]
    fake_pytesseract.image_to_string = staticmethod(  # type: ignore[attr-defined]
        lambda imagen, lang=None: f"TEXTO-FAKE[{getattr(imagen, 'nombre', 'pagina')}]"
    )
    fake_pil = types.ModuleType("PIL")
    fake_pil_image = types.ModuleType("PIL.Image")
    fake_pil_image.open = staticmethod(lambda ruta: _FakeImagen(nombre=Path(ruta).name))  # type: ignore[attr-defined]
    fake_pil.Image = fake_pil_image  # type: ignore[attr-defined]
    fake_pdf2image = types.ModuleType("pdf2image")
    fake_pdf2image.convert_from_path = staticmethod(  # type: ignore[attr-defined]
        lambda ruta, dpi=300: [_FakeImagen("p1"), _FakeImagen("p2")]
    )
    return {
        "pytesseract": fake_pytesseract,
        "PIL": fake_pil,
        "PIL.Image": fake_pil_image,
        "pdf2image": fake_pdf2image,
    }


class FakesOCR:
    """Contexto que instala la cadena OCR falsa y binarios visibles."""

    def __enter__(self):
        import shutil

        self._fakes = _modulos_fakes()
        self._reales = {nombre: sys.modules.get(nombre) for nombre in self._fakes}
        sys.modules.update(self._fakes)
        self._which_real = shutil.which
        shutil.which = lambda nombre: f"/fake/{nombre}"  # type: ignore[assignment]
        return self

    def __exit__(self, *exc):
        import shutil

        for nombre, modulo in self._reales.items():
            if modulo is None:
                sys.modules.pop(nombre, None)
            else:
                sys.modules[nombre] = modulo
        shutil.which = self._which_real  # type: ignore[assignment]
        return False


class BaseTemporal(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.addCleanup(self.temporal.cleanup)
        self.espacio = self.base / "espacio"


class TestOcrDocumento(BaseTemporal):
    def test_ocr_pdf_pagina_por_pagina(self) -> None:
        pdf = self.base / "escaneo.pdf"
        pdf.write_bytes(b"%PDF-fake")
        with FakesOCR():
            resultado = ocr.ocr(pdf)

        self.assertEqual(len(resultado["paginas"]), 2)
        self.assertIn("TEXTO-FAKE[p1]", resultado["texto"])
        self.assertEqual(resultado["metadatos"]["ocr"], "tesseract")

    def test_ocr_imagen(self) -> None:
        imagen = self.base / "foto.png"
        imagen.write_bytes(b"PNG-fake")
        with FakesOCR():
            resultado = ocr.ocr(imagen)

        self.assertEqual(len(resultado["paginas"]), 1)
        self.assertEqual(resultado["paginas"][0]["texto"], "TEXTO-FAKE[foto.png]")

    def test_ocr_extension_no_soportada(self) -> None:
        docx = self.base / "x.docx"
        docx.write_bytes(b"fake")
        with FakesOCR():
            with self.assertRaises(ValueError) as contexto:
                ocr.ocr(docx)
        self.assertIn("no soporta", str(contexto.exception))

    def test_ocr_archivo_inexistente(self) -> None:
        with FakesOCR():
            with self.assertRaises(ValueError) as contexto:
                ocr.ocr(self.base / "no-hay.pdf")
        self.assertIn("no existe", str(contexto.exception))

    def test_ocr_sin_cadena_falla_accionable(self) -> None:
        pdf = self.base / "escaneo.pdf"
        pdf.write_bytes(b"%PDF-fake")
        with mock.patch.dict(sys.modules, {"pytesseract": None, "pdf2image": None}):
            with mock.patch("shutil.which", return_value=None):
                with self.assertRaises(ValueError) as contexto:
                    ocr.ocr_pdf(pdf)
        self.assertIn("cadena OCR", str(contexto.exception))

    def test_paginas_solo_pdf(self) -> None:
        imagen = self.base / "foto.png"
        imagen.write_bytes(b"PNG-fake")
        with FakesOCR():
            with self.assertRaises(ValueError):
                ocr.ocr(imagen, max_paginas=1)

    def test_cli_json_y_texto(self) -> None:
        pdf = self.base / "escaneo.pdf"
        pdf.write_bytes(b"%PDF-fake")
        with FakesOCR():
            salida = io.StringIO()
            with redirect_stdout(salida):
                codigo = ocr.main([str(pdf), "--json"])
            self.assertEqual(codigo, 0)
            payload = json.loads(salida.getvalue())
            self.assertEqual(payload["metadatos"]["paginas"], "2")

            texto = io.StringIO()
            with redirect_stdout(texto):
                codigo = ocr.main([str(pdf), "--texto", "--max-caracteres", "5"])
            self.assertEqual(codigo, 0)
            self.assertEqual(texto.getvalue().strip(), "TEXTO"[:5])

    def test_cli_aviso_sin_texto_devuelve_2(self) -> None:
        pdf = self.base / "escaneo.pdf"
        pdf.write_bytes(b"%PDF-fake")
        with FakesOCR():
            with mock.patch.object(
                sys.modules["pytesseract"],
                "image_to_string",
                staticmethod(lambda imagen, lang=None: "  "),
            ):
                error = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(error):
                    codigo = ocr.main([str(pdf)])
        self.assertEqual(codigo, 2)
        self.assertIn("AVISO", error.getvalue())

    def test_cli_dpi_y_paginas_invalidos(self) -> None:
        pdf = self.base / "escaneo.pdf"
        pdf.write_bytes(b"%PDF-fake")
        with FakesOCR():
            with redirect_stderr(io.StringIO()):
                self.assertEqual(ocr.main([str(pdf), "--dpi", "0"]), 1)
                self.assertEqual(ocr.main([str(pdf), "--paginas", "-1"]), 1)

    def test_salida_dentro_de_entregables_y_sin_pisar(self) -> None:
        with FakesOCR():
            destino = ocr.guardar_salida("hola", Path("t.txt"), self.espacio)
            self.assertEqual(destino, (self.espacio.resolve() / "entregables" / "t.txt"))
            with self.assertRaises(ValueError):
                ocr.guardar_salida("otra", Path("t.txt"), self.espacio)
            with self.assertRaises(ValueError):
                ocr.guardar_salida("x", Path("/otra/cosa.txt"), self.espacio)
            with self.assertRaises(ValueError):
                ocr.guardar_salida("x", Path("t.pdf"), self.espacio)

    def test_cli_salida_guarda_transcripcion(self) -> None:
        pdf = self.base / "escaneo.pdf"
        pdf.write_bytes(b"%PDF-fake")
        with FakesOCR():
            with redirect_stdout(io.StringIO()):
                codigo = ocr.main(
                    [str(pdf), "--salida", "t.txt", "--workspace", str(self.espacio)]
                )
        self.assertEqual(codigo, 0)
        guardada = self.espacio / "entregables" / "t.txt"
        self.assertTrue(guardada.is_file())
        self.assertIn("TEXTO-FAKE", guardada.read_text(encoding="utf-8"))

    def test_selftest(self) -> None:
        self.assertEqual(ocr.selftest(), 0)


class TestIndiceConOcr(BaseTemporal):
    def test_con_ocr_guarda_texto_ocr_buscable(self) -> None:
        raiz = self.base / "selva"
        (raiz / "exp").mkdir(parents=True)
        pdf = raiz / "exp" / "escaneo.pdf"
        pdf.write_bytes(b"%PDF-falso")

        leer_real = ix.lector.leer
        ocr_real = ix.mod_ocr.ocr
        ix.lector.leer = lambda ruta: {  # type: ignore[assignment]
            "formato": "pdf",
            "metadatos": {},
            "paginas": [{"numero": 1, "texto": ""}],
            "texto": "",
            "aviso": "parece escaneado",
            "ok": True,
            "ruta": ruta.name,
            "bytes": 10,
        }
        ix.mod_ocr.ocr = lambda ruta, **kwargs: {  # type: ignore[assignment]
            "ok": True,
            "ruta": ruta.name,
            "bytes": 10,
            "formato": "pdf",
            "metadatos": {"ocr": "tesseract"},
            "paginas": [{"numero": 1, "texto": "CONTRATO FAKE POR OCR"}],
            "texto": "CONTRATO FAKE POR OCR",
        }
        try:
            resumen = ix.indexar(raiz, self.espacio, con_ocr=True)
        finally:
            ix.lector.leer = leer_real  # type: ignore[assignment]
            ix.mod_ocr.ocr = ocr_real  # type: ignore[assignment]

        self.assertEqual(resumen.get("con_ocr"), 1)
        indices = bd.cargar_indices(self.espacio)
        resultados, _ = bd.buscar(indices, consulta="contrato")
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["donde"], "ocr")
        self.assertIn("CONTRATO", resultados[0]["snippet"])

    def test_cambio_de_modo_no_reutiliza(self) -> None:
        raiz = self.base / "selva"
        (raiz / "exp").mkdir(parents=True)
        (raiz / "exp" / "nota.txt").write_text("hola", encoding="utf-8")

        sin_ocr = ix.indexar(raiz, self.espacio, con_ocr=False)
        self.assertGreater(sin_ocr["reutilizados"] + sin_ocr["nuevos"], 0)

        leer_real = ix.lector.leer
        ix.lector.leer = lambda ruta: {  # type: ignore[assignment]
            "formato": "txt",
            "metadatos": {},
            "texto": "",
            "aviso": "x",
            "ok": True,
            "ruta": ruta.name,
            "bytes": 4,
        }
        ocr_real = ix.mod_ocr.ocr
        ix.mod_ocr.ocr = lambda ruta, **kwargs: {"texto": "OCR", "paginas": []}  # type: ignore[assignment]
        try:
            con_ocr = ix.indexar(raiz, self.espacio, con_ocr=True)
        finally:
            ix.lector.leer = leer_real  # type: ignore[assignment]
            ix.mod_ocr.ocr = ocr_real  # type: ignore[assignment]
        self.assertEqual(con_ocr.get("reutilizados"), 0)

    def test_ocr_con_error_no_rompe_el_mapa(self) -> None:
        raiz = self.base / "selva"
        (raiz / "exp").mkdir(parents=True)
        pdf = raiz / "exp" / "roto.pdf"
        pdf.write_bytes(b"%PDF-falso")

        leer_real = ix.lector.leer
        ocr_real = ix.mod_ocr.ocr
        ix.lector.leer = lambda ruta: {  # type: ignore[assignment]
            "formato": "pdf",
            "metadatos": {},
            "paginas": [{"numero": 1, "texto": ""}],
            "texto": "",
            "aviso": "parece escaneado",
            "ok": True,
            "ruta": ruta.name,
            "bytes": 10,
        }

        def _ocr_roto(ruta, **kwargs):
            raise ValueError("falta la cadena OCR — tesseract: winget install ...")

        ix.mod_ocr.ocr = _ocr_roto  # type: ignore[assignment]
        try:
            resumen = ix.indexar(raiz, self.espacio, con_ocr=True)
        finally:
            ix.lector.leer = leer_real  # type: ignore[assignment]
            ix.mod_ocr.ocr = ocr_real  # type: ignore[assignment]

        self.assertEqual(resumen.get("ocr_errores"), 1)
        indice = ix.cargar(Path(resumen["indice"]))
        entrada = indice["archivos"][0]
        self.assertIsNone(entrada.get("texto_ocr"))
        self.assertIsNotNone(entrada.get("ocr_error"))

    def test_cli_con_ocr(self) -> None:
        raiz = self.base / "selva"
        (raiz / "exp").mkdir(parents=True)
        (raiz / "exp" / "nota.txt").write_text("hola mundo", encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            codigo = ix.main(
                ["--ruta", str(raiz), "--workspace", str(self.espacio), "--con-ocr"]
            )
        # Sin Tesseract real el OCR falla por archivo, pero el mapa se arma igual.
        self.assertEqual(codigo, 0)


class TestBuscarOcr(BaseTemporal):
    def test_donde_ocr_y_etiqueta(self) -> None:
        indices = [
            {
                "raiz": "/fake",
                "archivos": [
                    {
                        "ruta": "escaneo.pdf",
                        "nombre": "escaneo.pdf",
                        "carpeta": ".",
                        "extension": ".pdf",
                        "documento": True,
                        "escaneado": True,
                        "texto": "",
                        "texto_ocr": "CONTRATO RECONOCIDO",
                        "mtime": 1_700_000_000,
                    }
                ],
            }
        ]
        resultados, total = bd.buscar(indices, consulta="contrato")
        self.assertEqual(total, 1)
        self.assertEqual(resultados[0]["donde"], "ocr")
        self.assertTrue(resultados[0]["con_ocr"])


class TestInstaladorOcr(unittest.TestCase):
    def test_plan_con_ocr_incluye_puente(self) -> None:
        if sys.platform != "win32":
            self.skipTest("el instalador automático es sólo para Windows")
        estado = inst.leer_estado()
        if estado is None:
            self.skipTest("sin verificador no hay plan que mirar")
        programas, _, _, _ = inst.faltantes(estado)
        # La lista de tareas del --plan con OCR debe nombrar a pytesseract.
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = inst.main(["--plan", "--con-ocr"])
        self.assertEqual(codigo, 0)
        if "tesseract" in programas:
            self.assertIn("pytesseract", salida.getvalue())
        else:
            self.assertIn("No falta nada", salida.getvalue())


class TestMenuOcr(unittest.TestCase):
    def test_el_menu_ofrece_ocr(self) -> None:
        por_numero = {accion["numero"]: accion for accion in menu.ACCIONES}
        self.assertEqual(por_numero[14]["script"], "ocr_documento.py")
        self.assertIn("pide_ocr", menu.PIDE)

    def test_construir_comando_ocr_pasa_workspace(self) -> None:
        accion = menu.buscar_accion(14)
        comando = menu.construir_comando(accion, ["x.pdf", "--texto"], "D:\\espacio")
        self.assertIn("--workspace", comando)


if __name__ == "__main__":
    unittest.main()
