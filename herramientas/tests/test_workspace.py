"""Regresiones del espacio de trabajo (``--workspace`` y su variable de entorno).

Sólo biblioteca estándar: no toca el repositorio, todo ocurre en temporales.

    python -m unittest discover -s herramientas/tests -v
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "herramientas" / "scripts"))

import generar_documento as motor  # noqa: E402
import init_local  # noqa: E402
import listar_generadores  # noqa: E402
import nuevo_entregable  # noqa: E402
import verificar_limites  # noqa: E402
import workspace as ws  # noqa: E402

SPEC = {
    "tipo": "prueba",
    "titulo": "Prueba de workspace",
    "formato": "docx",
    "datos": {"entidad": "organizacion/entidad.csv"},
    "constantes": {},
    "bloques": [{"tipo": "parrafo", "texto": "{{entidad.razon_social}}"}],
}

GENERADOR = """\
import json
import pathlib
import sys

argumentos = sys.argv[1:]
entrada = argumentos[argumentos.index("--entrada") + 1]
payload = json.loads(pathlib.Path(entrada).read_text(encoding="utf-8"))
destino = pathlib.Path(payload["salida"])
destino.parent.mkdir(parents=True, exist_ok=True)
destino.write_text("ok " + payload["salida"], encoding="utf-8")
"""


class TestResolucion(unittest.TestCase):
    def test_por_defecto_es_la_zona_del_repositorio(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            self.assertEqual(ws.resolver(base=Path(temporal)), Path(temporal).resolve() / "usuario")

    def test_explicito_gana_sobre_la_variable_de_entorno(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            with mock.patch.dict(os.environ, {ws.VARIABLE_ENTORNO: str(base / "entorno")}):
                self.assertEqual(ws.resolver(base / "explicito", base=base), base / "explicito")

    def test_la_variable_de_entorno_gana_sobre_el_defecto(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            with mock.patch.dict(os.environ, {ws.VARIABLE_ENTORNO: str(base / "entorno")}):
                self.assertEqual(ws.resolver(base=base), base / "entorno")

    def test_mostrar_nunca_devuelve_una_ruta_absoluta_si_puede_evitarlo(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            espacio = Path(temporal) / "cliente-a"
            ruta = espacio / "entregables" / "word" / "x.docx"

            self.assertEqual(ws.mostrar(ruta, espacio), "entregables/word/x.docx")


class TestNuevoEntregable(unittest.TestCase):
    def test_resuelve_dentro_del_espacio_pedido(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            espacio = Path(temporal) / "cliente-a"

            ruta = nuevo_entregable.resolver(
                "word", "Informe de Prueba", "2026-11-25", espacio=espacio
            )

            self.assertEqual(
                ruta, espacio / "entregables" / "word" / "2026-11-25_informe-de-prueba.docx"
            )


class TestInitLocal(unittest.TestCase):
    def test_prepara_otro_espacio_de_trabajo(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            espacio = Path(temporal) / "cliente-a"

            with contextlib.redirect_stdout(io.StringIO()):
                codigo = init_local.main(["--workspace", str(espacio)])

            self.assertEqual(codigo, 0)
            for subcarpeta in ws.SUBCARPETAS:
                self.assertTrue((espacio / subcarpeta).is_dir(), subcarpeta)
            self.assertTrue((espacio / "datos" / "organizacion" / "entidad.csv").is_file())


class TestVerificarLimites(unittest.TestCase):
    def test_un_espacio_externo_no_falla_por_git(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            espacio = Path(temporal) / "cliente-a"
            (espacio / "datos").mkdir(parents=True)

            with contextlib.redirect_stdout(io.StringIO()) as salida:
                codigo = verificar_limites.main(["--workspace", str(espacio)])

            self.assertEqual(codigo, 0)
            self.assertIn("externo al repositorio", salida.getvalue())


class TestMotorConWorkspace(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.addCleanup(self.temporal.cleanup)

        self.espacio = self.base / "cliente-a"
        for subcarpeta in ws.SUBCARPETAS:
            (self.espacio / subcarpeta).mkdir(parents=True, exist_ok=True)
        (self.espacio / "datos" / "organizacion" / "entidad.csv").write_text(
            "clave,valor\nrazon_social,ACME S.A.C.\n", encoding="utf-8"
        )

        generador = self.espacio / "generadores" / "propio"
        generador.mkdir(parents=True, exist_ok=True)
        (generador / "generador.json").write_text(
            json.dumps({"nombre": "propio", "tipos": ["*"]}), encoding="utf-8"
        )
        (generador / "generador.py").write_text(GENERADOR, encoding="utf-8")

        self.specs = self.base / "specs"
        self.specs.mkdir()
        (self.specs / "prueba.json").write_text(
            json.dumps(SPEC, ensure_ascii=False), encoding="utf-8"
        )

        self.specs_original = motor.DIR_SPECS
        motor.DIR_SPECS = self.specs
        self.addCleanup(self._restaurar)

    def _restaurar(self) -> None:
        motor.DIR_SPECS = self.specs_original

    def test_genera_dentro_del_espacio_pedido(self) -> None:
        salida = self.espacio / "entregables" / "word" / "x.docx"

        with contextlib.redirect_stdout(io.StringIO()):
            codigo = motor.main(
                [
                    "--tipo",
                    "prueba",
                    "--workspace",
                    str(self.espacio),
                    "--salida",
                    str(salida),
                    "--json",
                ]
            )

        self.assertEqual(codigo, 0)
        self.assertTrue(salida.is_file())

    def test_la_salida_fuera_del_espacio_se_rechaza(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            codigo = motor.main(
                [
                    "--tipo",
                    "prueba",
                    "--workspace",
                    str(self.espacio),
                    "--salida",
                    str(self.base / "suelto.docx"),
                ]
            )

        self.assertEqual(codigo, 1)
        self.assertFalse((self.base / "suelto.docx").exists())

    def test_los_datos_salen_del_espacio_pedido(self) -> None:
        # Sin --datos: el motor debe leer <workspace>/datos, no la zona del repo.
        salida = self.espacio / "entregables" / "word" / "y.docx"

        with contextlib.redirect_stdout(io.StringIO()) as consola:
            codigo = motor.main(
                [
                    "--tipo",
                    "prueba",
                    "--workspace",
                    str(self.espacio),
                    "--salida",
                    str(salida),
                    "--json",
                ]
            )

        self.assertEqual(codigo, 0)
        self.assertIn("generador-usuario", consola.getvalue())


class TestListarGeneradores(unittest.TestCase):
    def test_lista_los_generadores_del_espacio_pedido(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            espacio = Path(temporal) / "cliente-a"
            carpeta = espacio / "generadores" / "propio"
            carpeta.mkdir(parents=True)
            (carpeta / "generador.json").write_text(
                json.dumps({"nombre": "propio", "tipos": ["informe"]}), encoding="utf-8"
            )
            (carpeta / "generador.py").write_text("print('x')\n", encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()) as consola:
                codigo = listar_generadores.main(["--workspace", str(espacio), "--json"])

            payload = json.loads(consola.getvalue())
            self.assertEqual(codigo, 0)
            self.assertEqual(payload["generadores"][0]["nombre"], "propio")
            self.assertEqual(
                payload["generadores"][0]["carpeta"], "generadores/propio"
            )


if __name__ == "__main__":
    unittest.main()
