"""Regresiones del arranque único (``empezar.py``).

Cubre que la preparación deje la zona del usuario lista sin pisar nada, que sea
idempotente, que respete los datos y las plantillas del usuario, que ``--plan``
no escriba y que el menú ofrezca la acción. Sólo biblioteca estándar.

    python -m unittest discover -s herramientas/tests -v
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
DIR_SCRIPTS = RAIZ / "herramientas" / "scripts"
sys.path.insert(0, str(DIR_SCRIPTS))

import empezar  # noqa: E402
import init_local  # noqa: E402
import menu  # noqa: E402
import plantillas as pl  # noqa: E402
import workspace as ws  # noqa: E402

CONTRATOS = sorted(init_local.DIR_CONTRATOS.glob("**/*.example"))


class BaseTemporal(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.espacio = self.base / "espacio"
        self.addCleanup(self.temporal.cleanup)

    def preparar(self, con_plantillas: bool = True) -> dict:
        with redirect_stdout(io.StringIO()):
            return empezar.preparar(self.espacio, con_plantillas=con_plantillas)


class TestPreparacion(BaseTemporal):
    def test_crea_carpetas_datos_y_plantillas(self) -> None:
        resultado = self.preparar()

        self.assertEqual(len(resultado["carpetas"]), len(ws.SUBCARPETAS))
        self.assertEqual(len(resultado["datos_creados"]), len(CONTRATOS))
        self.assertEqual(len(resultado["plantillas_creadas"]), len(pl.TIPOS))
        self.assertTrue((self.espacio / "datos" / "organizacion" / "entidad.csv").is_file())

    def test_cada_tipo_tiene_su_plantilla_base(self) -> None:
        self.preparar()

        carpeta = pl.carpeta_destino(self.espacio)
        for tipo in pl.TIPOS:
            with self.subTest(tipo=tipo):
                self.assertTrue(list(carpeta.glob(f"{tipo}-*")))

    def test_es_idempotente(self) -> None:
        self.preparar()
        segunda = self.preparar()

        self.assertEqual(segunda["carpetas"], [])
        self.assertEqual(segunda["datos_creados"], [])
        self.assertEqual(segunda["plantillas_creadas"], [])
        self.assertEqual(len(segunda["datos_respetados"]), len(CONTRATOS))

    def test_respeta_los_datos_del_usuario(self) -> None:
        entidad = self.espacio / "datos" / "organizacion" / "entidad.csv"
        entidad.parent.mkdir(parents=True)
        entidad.write_text("MI DATO REAL", encoding="utf-8")

        resultado = self.preparar()

        self.assertEqual(entidad.read_text(encoding="utf-8"), "MI DATO REAL")
        self.assertIn(entidad, resultado["datos_respetados"])
        self.assertNotIn(entidad, resultado["datos_creados"])

    def test_no_duplica_una_plantilla_que_ya_existe(self) -> None:
        carpeta = pl.carpeta_destino(self.espacio)
        carpeta.mkdir(parents=True)
        (carpeta / "informe-mia.docx").write_bytes(b"mia")

        resultado = self.preparar()

        self.assertIn("informe", resultado["plantillas_existentes"])
        self.assertEqual(len(resultado["plantillas_creadas"]), len(pl.TIPOS) - 1)
        self.assertEqual((carpeta / "informe-mia.docx").read_bytes(), b"mia")

    def test_sin_plantillas_solo_prepara_estructura_y_datos(self) -> None:
        resultado = self.preparar(con_plantillas=False)

        self.assertEqual(resultado["plantillas_creadas"], [])
        self.assertEqual(len(resultado["carpetas"]), len(ws.SUBCARPETAS))
        self.assertEqual(len(resultado["datos_creados"]), len(CONTRATOS))
        self.assertEqual(list(pl.carpeta_destino(self.espacio).glob("*")), [])


class TestPlan(BaseTemporal):
    def test_plan_no_escribe_nada(self) -> None:
        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = empezar.mostrar_plan(
                self.espacio,
                {"faltantes_obligatorios": [], "faltantes_opcionales": []},
            )

        self.assertEqual(codigo, 0)
        self.assertFalse(self.espacio.exists())
        self.assertIn("por crear", salida.getvalue())

    def test_plan_de_espacio_completo_lo_dice(self) -> None:
        self.preparar()
        salida = io.StringIO()
        with redirect_stdout(salida):
            empezar.mostrar_plan(
                self.espacio,
                {"faltantes_obligatorios": [], "faltantes_opcionales": []},
            )

        self.assertIn("Nada que preparar", salida.getvalue())


class TestMain(BaseTemporal):
    def correr(self, argumentos: list[str]) -> int:
        with redirect_stdout(io.StringIO()):
            return empezar.main(argumentos + ["--workspace", str(self.espacio)])

    def test_entorno_completo_devuelve_cero(self) -> None:
        estado = {"faltantes_obligatorios": [], "faltantes_opcionales": []}
        with mock.patch.object(empezar, "_verificar", return_value=estado):
            codigo = self.correr(["--si", "--sin-instalar"])

        self.assertEqual(codigo, 0)
        self.assertTrue((self.espacio / "datos" / "organizacion" / "entidad.csv").is_file())

    def test_faltante_obligatorio_devuelve_uno_pero_prepara(self) -> None:
        estado = {"faltantes_obligatorios": ["pandoc"], "faltantes_opcionales": []}
        with mock.patch.object(empezar, "_verificar", return_value=estado):
            codigo = self.correr(["--si", "--sin-instalar"])

        self.assertEqual(codigo, 1)
        self.assertTrue((self.espacio / "datos" / "organizacion" / "entidad.csv").is_file())
        self.assertTrue(list(pl.carpeta_destino(self.espacio).glob("*")))

    def test_sin_plantillas_no_las_crea(self) -> None:
        estado = {"faltantes_obligatorios": [], "faltantes_opcionales": []}
        with mock.patch.object(empezar, "_verificar", return_value=estado):
            codigo = self.correr(["--si", "--sin-instalar", "--sin-plantillas"])

        self.assertEqual(codigo, 0)
        self.assertEqual(list(pl.carpeta_destino(self.espacio).glob("*")), [])

    def test_selftest(self) -> None:
        with redirect_stdout(io.StringIO()):
            self.assertEqual(empezar.selftest(), 0)


class TestMenu(BaseTemporal):
    def test_el_menu_ofrece_el_primer_arranque(self) -> None:
        accion = menu.buscar_accion(15)

        self.assertIsNotNone(accion)
        self.assertEqual(accion["script"], "empezar.py")
        self.assertTrue(accion["workspace"])

    def test_detecta_que_falta_el_primer_arranque(self) -> None:
        self.assertTrue(menu.necesita_primer_arranque(str(self.espacio)))

        with redirect_stdout(io.StringIO()):
            empezar.preparar(self.espacio)

        self.assertFalse(menu.necesita_primer_arranque(str(self.espacio)))

    def test_el_menu_sugiere_la_opcion_cuando_falta(self) -> None:
        salida = io.StringIO()
        with redirect_stdout(salida):
            menu.mostrar_menu(str(self.espacio))

        self.assertIn("opción 15", salida.getvalue())

    def test_el_menu_no_sugiere_cuando_ya_esta_preparado(self) -> None:
        with redirect_stdout(io.StringIO()):
            empezar.preparar(self.espacio)

        salida = io.StringIO()
        with redirect_stdout(salida):
            menu.mostrar_menu(str(self.espacio))

        self.assertNotIn("Primera vez", salida.getvalue())


if __name__ == "__main__":
    unittest.main()
