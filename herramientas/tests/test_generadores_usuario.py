"""Regresiones del contrato de generadores propios del usuario.

Un generador propio es código del usuario: vive en ``usuario/generadores/``,
no se versiona y el agente no lo modifica. Estas pruebas nunca escriben en
``usuario/``: usan directorios temporales.

Sólo biblioteca estándar. Se ejecuta con:

    python -m unittest discover -s herramientas/tests -v
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "herramientas" / "scripts"))

import generar_documento as motor  # noqa: E402  (import tras ajustar sys.path)
import generadores_usuario as gu  # noqa: E402

SCRIPT_OK = """\
import json
import pathlib
import sys

argumentos = sys.argv[1:]
entrada = argumentos[argumentos.index("--entrada") + 1]
payload = json.loads(pathlib.Path(entrada).read_text(encoding="utf-8"))
destino = pathlib.Path(payload["salida"])
destino.parent.mkdir(parents=True, exist_ok=True)
destino.write_text("DOCX " + payload["titulo"], encoding="utf-8")
"""

SCRIPT_FALLA = """\
import sys

sys.stderr.write("no puedo generar el documento\\n")
sys.exit(1)
"""

SCRIPT_SILENCIO = """\
import sys

sys.exit(0)
"""


def escribir_generador(
    base: Path,
    nombre: str,
    tipos: list[str],
    script: str = SCRIPT_OK,
    manifiesto_extra: dict | None = None,
    archivo_script: str = "generador.py",
) -> Path:
    """Crea un generador de prueba dentro de un directorio temporal."""
    carpeta = base / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    manifiesto = {"nombre": nombre, "tipos": tipos}
    if manifiesto_extra:
        manifiesto.update(manifiesto_extra)
    (carpeta / gu.NOMBRE_MANIFIESTO).write_text(
        json.dumps(manifiesto, ensure_ascii=False), encoding="utf-8"
    )
    (carpeta / archivo_script).write_text(script, encoding="utf-8")
    return carpeta


class TestDescubrimiento(unittest.TestCase):
    def test_encuentra_el_generador_por_manifiesto(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            escribir_generador(base, "mi-plantilla", ["informe", "memorandum"])

            generadores = gu.descubrir(base)

            self.assertEqual(len(generadores), 1)
            self.assertEqual(generadores[0].nombre, "mi-plantilla")
            self.assertEqual(generadores[0].tipos, ("informe", "memorandum"))
            self.assertEqual(generadores[0].comando, ("python",))
            self.assertTrue(generadores[0].cubre("informe"))
            self.assertFalse(generadores[0].cubre("acta"))

    def test_el_comando_por_defecto_de_javascript_es_node(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            escribir_generador(base, "js", ["informe"], archivo_script="generador.js")

            generadores = gu.descubrir(base)

            self.assertEqual(generadores[0].comando, ("node",))

    def test_manifiesto_sin_tipos_falla_con_mensaje_claro(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            carpeta = base / "roto"
            carpeta.mkdir()
            (carpeta / gu.NOMBRE_MANIFIESTO).write_text(
                json.dumps({"nombre": "roto"}), encoding="utf-8"
            )

            with self.assertRaises(ValueError) as ctx:
                gu.descubrir(base)

            self.assertIn("tipos", str(ctx.exception))

    def test_script_declarado_inexistente_falla(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            carpeta = base / "roto"
            carpeta.mkdir()
            (carpeta / gu.NOMBRE_MANIFIESTO).write_text(
                json.dumps({"nombre": "roto", "tipos": ["informe"], "script": "no-existe.py"}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError) as ctx:
                gu.descubrir(base)

            self.assertIn("no-existe.py", str(ctx.exception))

    def test_directorio_inexistente_no_falla(self) -> None:
        self.assertEqual(gu.descubrir(Path("no-existe-esta-carpeta")), [])


class TestSeleccion(unittest.TestCase):
    def test_selecciona_el_generador_que_declara_el_tipo(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            escribir_generador(base, "uno", ["informe"])
            escribir_generador(base, "dos", ["memorandum"])

            generador = gu.seleccionar(gu.descubrir(base), "informe")

            self.assertIsNotNone(generador)
            self.assertEqual(generador.nombre, "uno")

    def test_sin_generador_para_el_tipo_devuelve_none(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            escribir_generador(base, "uno", ["informe"])

            self.assertIsNone(gu.seleccionar(gu.descubrir(base), "acta"))

    def test_dos_generadores_para_el_mismo_tipo_fallan_en_vez_de_elegir_solos(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            escribir_generador(base, "uno", ["informe"])
            escribir_generador(base, "dos", ["informe"])

            with self.assertRaises(ValueError) as ctx:
                gu.seleccionar(gu.descubrir(base), "informe")

            self.assertIn("'uno'", str(ctx.exception))
            self.assertIn("'dos'", str(ctx.exception))

    def test_el_generador_asterisco_sirve_para_cualquier_tipo(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            escribir_generador(base, "todos", ["*"])

            generador = gu.seleccionar(gu.descubrir(base), "acta")

            self.assertIsNotNone(generador)
            self.assertEqual(generador.nombre, "todos")

    def test_el_tipo_explícito_gana_sobre_el_asterisco(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            escribir_generador(base, "todos", ["*"])
            escribir_generador(base, "informe", ["informe"])

            generador = gu.seleccionar(gu.descubrir(base), "informe")

            self.assertEqual(generador.nombre, "informe")


class TestPayloadDelGenerador(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = {
            "tipo": "informe",
            "titulo": "Informe Ejecutivo",
            "formato": "docx",
            "constantes": {"anio": "2026"},
        }
        self.datos = {
            "entidad": {
                "cabecera": ["clave", "valor"],
                "filas": [["razon_social", "ACME S.A.C."]],
            },
            "tablas": {
                "cabecera": ["codigo", "monto"],
                "filas": [["P-001", "10.00"]],
            },
        }

    def test_el_payload_trae_contenido_resuelto_y_datos_crudos(self) -> None:
        bloques = [{"tipo": "parrafo", "texto": "ACME S.A.C."}]
        indice = [{"texto": "Resumen", "pagina": 1}]

        payload = gu.construir_payload(
            self.spec, self.datos, bloques, indice, "usuario/entregables/word/x.docx", {"anio": "2026"}
        )

        self.assertEqual(payload["tipo"], "informe")
        self.assertEqual(payload["bloques"], bloques)
        self.assertEqual(payload["indice"], indice)
        self.assertEqual(payload["entidad"]["razon_social"], "ACME S.A.C.")
        self.assertEqual(payload["datos"]["tablas"]["filas"], [["P-001", "10.00"]])
        self.assertEqual(payload["salida"], "usuario/entregables/word/x.docx")
        self.assertEqual(payload["constantes"], {"anio": "2026"})

    def test_el_payload_no_lleva_rutas_absolutas(self) -> None:
        payload = gu.construir_payload(
            self.spec, self.datos, [], [], "usuario/entregables/word/x.docx"
        )

        serializado = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn(str(RAIZ), serializado)
        self.assertNotIn("C:\\", serializado)

    def test_una_salida_absoluta_se_rechaza(self) -> None:
        with self.assertRaises(ValueError):
            gu.construir_payload(self.spec, self.datos, [], [], "C:/tmp/x.docx")


class TestEjecucionDelGenerador(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.addCleanup(self.temporal.cleanup)

    def _payload(self, salida: str = "usuario/entregables/word/x.docx") -> dict:
        return {
            "version": 1,
            "tipo": "informe",
            "titulo": "Informe Ejecutivo",
            "formato": "docx",
            "salida": salida,
            "bloques": [],
            "indice": [],
            "entidad": {},
            "datos": {},
            "constantes": {},
        }

    def test_el_generador_escribe_el_archivo_y_devuelve_la_ruta(self) -> None:
        escribir_generador(self.base, "ok", ["informe"])
        generador = gu.cargar(self.base / "ok")

        ruta = gu.ejecutar(generador, self._payload(), raiz=self.base)

        self.assertTrue(ruta.is_file())
        self.assertEqual(ruta.read_text(encoding="utf-8"), "DOCX Informe Ejecutivo")

    def test_un_generador_que_falla_reporta_su_error_textual(self) -> None:
        escribir_generador(self.base, "falla", ["informe"], script=SCRIPT_FALLA)
        generador = gu.cargar(self.base / "falla")

        with self.assertRaises(ValueError) as ctx:
            gu.ejecutar(generador, self._payload(), raiz=self.base)

        self.assertIn("no puedo generar el documento", str(ctx.exception))
        self.assertFalse((self.base / "usuario/entregables/word/x.docx").exists())

    def test_un_generador_que_no_escribe_nada_falla(self) -> None:
        escribir_generador(self.base, "silencio", ["informe"], script=SCRIPT_SILENCIO)
        generador = gu.cargar(self.base / "silencio")

        with self.assertRaises(ValueError) as ctx:
            gu.ejecutar(generador, self._payload(), raiz=self.base)

        self.assertIn("no produjo un archivo válido", str(ctx.exception))


class TestMotorConGeneradorPropio(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.addCleanup(self.temporal.cleanup)

        (self.base / "usuario" / "entregables" / "word").mkdir(parents=True)
        (self.base / "usuario" / "generadores").mkdir(parents=True)
        escribir_generador(self.base / "usuario" / "generadores", "mi-plantilla", ["informe"])

        self.specs = self.base / "specs"
        self.specs.mkdir()
        (self.specs / "informe.json").write_text(
            json.dumps(
                {
                    "tipo": "informe",
                    "titulo": "Informe Ejecutivo",
                    "formato": "docx",
                    "datos": {"entidad": "organizacion/entidad.csv"},
                    "constantes": {},
                    "bloques": [{"tipo": "parrafo", "texto": "{{entidad.razon_social}}"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        datos = self.base / "datos" / "organizacion"
        datos.mkdir(parents=True)
        (datos / "entidad.csv").write_text(
            "clave,valor\nrazon_social,ACME S.A.C.\n", encoding="utf-8"
        )

        self.raiz_original = motor.RAIZ
        self.specs_original = motor.DIR_SPECS
        motor.RAIZ = self.base
        motor.DIR_SPECS = self.specs
        self.addCleanup(self._restaurar)

    def _restaurar(self) -> None:
        motor.RAIZ = self.raiz_original
        motor.DIR_SPECS = self.specs_original

    def test_el_motor_usa_el_generador_del_usuario(self) -> None:
        salida = self.base / "usuario" / "entregables" / "word" / "informe.docx"

        with contextlib.redirect_stdout(io.StringIO()):
            codigo = motor.main(
                [
                    "--tipo",
                    "informe",
                    "--datos",
                    str(self.base / "datos"),
                    "--salida",
                    str(salida),
                    "--json",
                ]
            )

        self.assertEqual(codigo, 0)
        self.assertTrue(salida.is_file())
        self.assertEqual(salida.read_text(encoding="utf-8"), "DOCX Informe Ejecutivo")

    def test_sin_generador_se_ignora_el_del_usuario(self) -> None:
        args = argparse.Namespace(generador=None, sin_generador=True)

        self.assertIsNone(motor._elegir_generador(args, "informe"))

    def test_se_elige_el_generador_que_declara_el_tipo(self) -> None:
        escribir_generador(self.base / "usuario" / "generadores", "otro", ["acta"])
        args = argparse.Namespace(generador=None, sin_generador=False)

        generador = motor._elegir_generador(args, "informe")

        self.assertEqual(generador.nombre, "mi-plantilla")

    def test_un_generador_explicito_que_no_declara_el_tipo_falla(self) -> None:
        carpeta = escribir_generador(self.base / "usuario" / "generadores", "otro", ["acta"])
        args = argparse.Namespace(generador=str(carpeta), sin_generador=False)

        with self.assertRaises(ValueError) as ctx:
            motor._elegir_generador(args, "informe")

        self.assertIn("no declara el tipo", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
