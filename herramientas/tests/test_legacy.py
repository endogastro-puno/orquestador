"""Regresiones de los formatos viejos de Office (`.doc`, `.xls`, `.rtf`, `.odt`, `.ods`).

LibreOffice no está en CI: `subprocess.run` se sustituye por un fake que escribe
la conversión esperada. Así se prueba la lógica (conversión a temporal, formato
original, error accionable, integración con el índice) sin instalar nada.

    python -m unittest discover -s herramientas/tests -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
DIR_SCRIPTS = RAIZ / "herramientas" / "scripts"
sys.path.insert(0, str(DIR_SCRIPTS))

import buscar_documentos as bd  # noqa: E402
import indexar_documentos as ix  # noqa: E402
import leer_documento as ld  # noqa: E402
import nueva_plantilla as np  # noqa: E402


def _comando_a_salida(comando: list[str]) -> tuple[str, Path, Path]:
    """Extrae (formato destino, carpeta de salida, archivo origen) del comando."""
    destino = comando[comando.index("--convert-to") + 1]
    trabajo = Path(comando[comando.index("--outdir") + 1])
    origen = Path(comando[-1])
    return destino, trabajo, origen


def _conversion_ok(comando, **kwargs):
    """Fake de LibreOffice: escribe un OOXML válido donde lo pediría soffice."""
    destino, trabajo, origen = _comando_a_salida(comando)
    salida = trabajo / f"{origen.stem}.{destino}"
    if destino == "docx":
        np.crear_docx(salida)
    else:
        import openpyxl  # type: ignore

        libro = openpyxl.Workbook()
        libro.active["A1"] = "PLANILLA VIEJA"
        libro.save(salida)
    return SimpleNamespace(returncode=0, stdout="convertido", stderr="")


def _conversion_fallida(comando, **kwargs):
    return SimpleNamespace(returncode=1, stdout="", stderr="Error: no se pudo abrir")


class BaseTemporal(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.addCleanup(self.temporal.cleanup)

    def _archivo(self, nombre: str, contenido: bytes = b"binario-viejo") -> Path:
        ruta = self.base / nombre
        ruta.write_bytes(contenido)
        return ruta


class TestLeerLegacy(BaseTemporal):
    def test_doc_se_convierte_y_conserva_el_formato_original(self) -> None:
        ruta = self._archivo("expediente.doc")
        with mock.patch.object(ld, "_soffice", return_value="C:/fake/soffice.exe"):
            with mock.patch.object(ld.subprocess, "run", side_effect=_conversion_ok):
                resultado = ld.leer(ruta)

        self.assertEqual(resultado["formato"], "doc")
        self.assertIn("titulo", resultado["texto"])
        self.assertEqual(resultado["metadatos"]["convertido_con"], "libreoffice")
        self.assertEqual(resultado["metadatos"]["convertido_a"], ".docx")

    def test_xls_se_convierte_y_lee_las_hojas(self) -> None:
        ruta = self._archivo("tarifas.xls")
        with mock.patch.object(ld, "_soffice", return_value="C:/fake/soffice.exe"):
            with mock.patch.object(ld.subprocess, "run", side_effect=_conversion_ok):
                resultado = ld.leer(ruta)

        self.assertEqual(resultado["formato"], "xls")
        self.assertIn("hojas", resultado)
        self.assertIn("PLANILLA VIEJA", resultado["texto"])

    def test_no_modifica_el_original(self) -> None:
        original = b"\xd0\xcf\x11\xe0 contenido que no se debe tocar"
        ruta = self._archivo("viejo.doc", original)
        antes = ruta.stat().st_mtime_ns

        with mock.patch.object(ld, "_soffice", return_value="C:/fake/soffice.exe"):
            with mock.patch.object(ld.subprocess, "run", side_effect=_conversion_ok):
                ld.leer(ruta)

        self.assertEqual(ruta.read_bytes(), original)
        self.assertEqual(ruta.stat().st_mtime_ns, antes)

    def test_sin_libreoffice_falla_accionable(self) -> None:
        ruta = self._archivo("viejo.doc")
        with mock.patch.object(ld, "_soffice", return_value=None):
            with self.assertRaises(ValueError) as contexto:
                ld.leer(ruta)

        mensaje = str(contexto.exception)
        self.assertIn("LibreOffice", mensaje)
        self.assertIn("winget", mensaje)
        self.assertIn("original no se toca", mensaje)

    def test_conversion_fallida_no_inventa_texto(self) -> None:
        ruta = self._archivo("roto.doc")
        with mock.patch.object(ld, "_soffice", return_value="C:/fake/soffice.exe"):
            with mock.patch.object(ld.subprocess, "run", side_effect=_conversion_fallida):
                with self.assertRaises(ValueError) as contexto:
                    ld.leer(ruta)

        self.assertIn("no pudo convertir", str(contexto.exception))

    def test_timeout_es_error_claro(self) -> None:
        ruta = self._archivo("lento.doc")
        with mock.patch.object(ld, "_soffice", return_value="C:/fake/soffice.exe"):
            with mock.patch.object(
                ld.subprocess,
                "run",
                side_effect=ld.subprocess.TimeoutExpired(["soffice"], 180),
            ):
                with self.assertRaises(ValueError) as contexto:
                    ld.leer(ruta)

        self.assertIn("180 s", str(contexto.exception))

    def test_cli_json_reporta_el_formato_original(self) -> None:
        ruta = self._archivo("acta.rtf")
        with mock.patch.object(ld, "_soffice", return_value="C:/fake/soffice.exe"):
            with mock.patch.object(ld.subprocess, "run", side_effect=_conversion_ok):
                salida = io.StringIO()
                with redirect_stdout(salida):
                    codigo = ld.main([str(ruta), "--json"])

        self.assertEqual(codigo, 0)
        payload = json.loads(salida.getvalue())
        self.assertEqual(payload["formato"], "rtf")
        self.assertEqual(payload["metadatos"]["convertido_a"], ".docx")

    def test_docm_y_xlsm_se_leen_directo_sin_libreoffice(self) -> None:
        docm = self.base / "con-macros.docm"
        np.crear_docx(docm)
        with mock.patch.object(ld, "_soffice", return_value=None):
            resultado = ld.leer(docm)
        self.assertEqual(resultado["formato"], "docm")
        self.assertIn("titulo", resultado["texto"])

        xlsm = self.base / "con-macros.xlsm"
        import openpyxl  # type: ignore

        libro = openpyxl.Workbook()
        libro.active["A1"] = "MACROS"
        libro.save(xlsm)
        with mock.patch.object(ld, "_soffice", return_value=None):
            resultado = ld.leer(xlsm)
        self.assertEqual(resultado["formato"], "xlsm")
        self.assertIn("MACROS", resultado["texto"])

    def test_extensiones_legacy_registradas(self) -> None:
        for extension in ld.LEGACY:
            self.assertIn(extension, ld.LECTORES)
            self.assertIn(extension, ld.SOPORTADOS)


class TestIndiceLegacy(BaseTemporal):
    def test_doc_indexado_y_encontrado_por_contenido(self) -> None:
        raiz = self.base / "selva"
        (raiz / "FOLDER 1").mkdir(parents=True)
        (raiz / "FOLDER 1" / "contrato-viejo.doc").write_bytes(b"\xd0\xcf\x11\xe0")
        espacio = self.base / "espacio"

        with mock.patch.object(ld, "_soffice", return_value="C:/fake/soffice.exe"):
            with mock.patch.object(ld.subprocess, "run", side_effect=_conversion_ok):
                resumen = ix.indexar(raiz, espacio)

        self.assertEqual(resumen["total"], 1)
        self.assertEqual(resumen["convertidos"], 1)
        indice = ix.cargar(Path(resumen["indice"]))
        entrada = indice["archivos"][0]
        self.assertEqual(entrada["extension"], ".doc")
        self.assertIn("titulo", entrada["texto"])

        resultados, _ = bd.buscar(bd.cargar_indices(espacio), consulta="titulo")
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["ruta"], "FOLDER 1/contrato-viejo.doc")


if __name__ == "__main__":
    unittest.main()
