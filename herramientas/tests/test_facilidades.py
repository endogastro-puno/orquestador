"""Regresiones de las facilidades para el usuario final.

Cubre el módulo de plantillas, la instalación de plantillas propias, la
creación de plantillas iniciales, el menú y la lectura de imágenes. Sólo
biblioteca estándar, salvo la plantilla `.xlsx` y el OCR, que se saltean si
la dependencia no está instalada.

    python -m unittest discover -s herramientas/tests -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_SCRIPTS = RAIZ / "herramientas" / "scripts"
sys.path.insert(0, str(DIR_SCRIPTS))

import instalar_plantilla as ip  # noqa: E402
import leer_documento as lector  # noqa: E402
import menu  # noqa: E402
import nueva_plantilla as np_  # noqa: E402
import plantillas as pl  # noqa: E402


class BaseTemporal(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.base = Path(self.temporal.name)
        self.addCleanup(self.temporal.cleanup)


class TestPlantillasModulo(BaseTemporal):
    def test_slug_sin_espacios_ni_mayusculas(self) -> None:
        self.assertEqual(pl.slug("Corporativa"), "corporativa")
        self.assertEqual(pl.slug("MEMBRETE 2026"), "membrete-2026")
        self.assertEqual(pl.slug("con tildes: organización"), "con-tildes-organizacion")

    def test_nombre_canonico(self) -> None:
        self.assertEqual(pl.nombre("informe", "Base", "docx"), "informe-base.docx")

    def test_nombre_rechaza_variante_vacia(self) -> None:
        with self.assertRaises(ValueError):
            pl.nombre("informe", "---", "docx")

    def test_extension_valida_se_normaliza(self) -> None:
        self.assertEqual(pl.validar("oficio", ".DOCX"), "docx")

    def test_extension_invalida_para_el_tipo(self) -> None:
        with self.assertRaises(ValueError):
            pl.validar("reporte", "docx")

    def test_tipo_desconocido(self) -> None:
        with self.assertRaises(ValueError):
            pl.extensiones_de("inventado")

    def test_instalar_copia_sin_tocar_el_original(self) -> None:
        origen = self.base / "mia.docx"
        origen.write_bytes(b"contenido")

        destino = pl.instalar(origen, self.base, "oficio", "Corporativa")

        self.assertEqual(
            destino, self.base / "plantillas" / "propias" / "oficio-corporativa.docx"
        )
        self.assertEqual(destino.read_bytes(), b"contenido")
        self.assertTrue(origen.is_file())

    def test_instalar_colision_rechazada(self) -> None:
        origen = self.base / "mia.docx"
        origen.write_bytes(b"contenido")

        pl.instalar(origen, self.base, "oficio", "Corporativa")

        with self.assertRaises(ValueError) as contexto:
            pl.instalar(origen, self.base, "oficio", "Corporativa")
        self.assertIn("ya existe", str(contexto.exception))

    def test_instalar_en_oficiales(self) -> None:
        origen = self.base / "mia.docx"
        origen.write_bytes(b"contenido")

        destino = pl.instalar(origen, self.base, "oficio", "Corp", oficiales=True)

        self.assertEqual(destino.parent.name, "oficiales")

    def test_instalar_origen_inexistente(self) -> None:
        with self.assertRaises(ValueError):
            pl.instalar(self.base / "no-hay.docx", self.base, "oficio", "Corp")

    def test_selftest_del_modulo(self) -> None:
        self.assertEqual(pl.selftest(), 0)


class TestInstalarPlantillaCli(BaseTemporal):
    def test_instala_y_devuelve_cero(self) -> None:
        origen = self.base / "plantilla-de-la-oficina.docx"
        origen.write_bytes(b"contenido")
        espacio = self.base / "mi-espacio"

        codigo = ip.main(
            [
                "--origen",
                str(origen),
                "--tipo",
                "oficio",
                "--variante",
                "Corporativa",
                "--workspace",
                str(espacio),
            ]
        )

        self.assertEqual(codigo, 0)
        self.assertTrue((espacio / "plantillas" / "propias" / "oficio-corporativa.docx").is_file())

    def test_colision_devuelve_uno(self) -> None:
        origen = self.base / "mia.docx"
        origen.write_bytes(b"contenido")

        argumentos = [
            "--origen",
            str(origen),
            "--tipo",
            "oficio",
            "--variante",
            "base",
            "--workspace",
            str(self.base / "espacio"),
        ]
        self.assertEqual(ip.main(argumentos), 0)
        self.assertEqual(ip.main(argumentos), 1)

    def test_extension_invalida_devuelve_uno(self) -> None:
        origen = self.base / "mia.docx"
        origen.write_bytes(b"contenido")

        codigo = ip.main(
            [
                "--origen",
                str(origen),
                "--tipo",
                "reporte",
                "--workspace",
                str(self.base / "espacio"),
            ]
        )

        self.assertEqual(codigo, 1)

    def test_origen_inexistente_devuelve_uno(self) -> None:
        codigo = ip.main(
            [
                "--origen",
                str(self.base / "no-hay.docx"),
                "--tipo",
                "oficio",
                "--workspace",
                str(self.base / "espacio"),
            ]
        )

        self.assertEqual(codigo, 1)


class TestNuevaPlantilla(BaseTemporal):
    def test_crea_md(self) -> None:
        codigo = np_.main(["--tipo", "informe", "--formato", "md", "--workspace", str(self.base)])

        self.assertEqual(codigo, 0)
        destino = self.base / "plantillas" / "propias" / "informe-base.md"
        self.assertTrue(destino.is_file())
        self.assertIn("{{titulo}}", destino.read_text(encoding="utf-8"))

    def test_crea_docx_valido_que_el_lector_puede_leer(self) -> None:
        codigo = np_.main(["--tipo", "oficio", "--workspace", str(self.base)])

        self.assertEqual(codigo, 0)
        destino = self.base / "plantillas" / "propias" / "oficio-base.docx"
        self.assertTrue(destino.is_file())

        with zipfile.ZipFile(destino) as paquete:
            self.assertIn("word/document.xml", paquete.namelist())

        resultado = lector.leer(destino)
        self.assertIn("{{titulo}}", resultado["texto"])

    def test_crea_xlsx(self) -> None:
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            self.skipTest("sin openpyxl no se puede probar la plantilla .xlsx")

        codigo = np_.main(["--tipo", "reporte", "--workspace", str(self.base)])

        self.assertEqual(codigo, 0)
        self.assertTrue((self.base / "plantillas" / "propias" / "reporte-base.xlsx").is_file())

    def test_formato_rechazado_para_el_tipo(self) -> None:
        codigo = np_.main(["--tipo", "reporte", "--formato", "docx", "--workspace", str(self.base)])

        self.assertEqual(codigo, 1)

    def test_colision_devuelve_uno(self) -> None:
        argumentos = ["--tipo", "informe", "--workspace", str(self.base)]
        self.assertEqual(np_.main(argumentos), 0)
        self.assertEqual(np_.main(argumentos), 1)

    def test_selftest(self) -> None:
        self.assertEqual(np_.selftest(), 0)


class TestMenu(BaseTemporal):
    def test_cada_accion_apunta_a_un_script_real(self) -> None:
        for accion in menu.ACCIONES:
            with self.subTest(accion=accion["numero"]):
                self.assertTrue((menu.DIR_SCRIPTS / accion["script"]).is_file())

    def test_numeros_consecutivos_y_unicos(self) -> None:
        numeros = [accion["numero"] for accion in menu.ACCIONES]
        self.assertEqual(numeros, list(range(1, len(numeros) + 1)))

    def test_buscar_accion_fuera_de_rango(self) -> None:
        self.assertIsNone(menu.buscar_accion(0))
        self.assertIsNone(menu.buscar_accion(len(menu.ACCIONES) + 1))

    def test_descubre_tipos_declarativos(self) -> None:
        descubiertos = menu.tipos_declarativos()
        self.assertIn("manual", descubiertos)
        self.assertIn("plan-operativo", descubiertos)

    def test_opcion_directa_corre_el_script(self) -> None:
        espacio = self.base / "mi-espacio"

        codigo = menu.main(["--opcion", "10", "--workspace", str(espacio)])

        self.assertEqual(codigo, 0)

    def test_opcion_cero_sale(self) -> None:
        self.assertEqual(menu.main(["--opcion", "0"]), 0)

    def test_opcion_inexistente_devuelve_uno(self) -> None:
        self.assertEqual(menu.main(["--opcion", "99"]), 1)

    def test_construir_comando_pasa_workspace_solo_si_el_script_lo_acepta(self) -> None:
        accion = menu.buscar_accion(4)  # validar_datos: acepta --workspace
        comando = menu.construir_comando(accion, [], "D:\\mi-espacio")
        self.assertIn("--workspace", comando)

        accion_sin = menu.buscar_accion(1)  # verificar_entorno: no lo acepta
        comando_sin = menu.construir_comando(accion_sin, [], "D:\\mi-espacio")
        self.assertNotIn("--workspace", comando_sin)

    def test_selftest(self) -> None:
        self.assertEqual(menu.selftest(), 0)


class TestLecturaDeImagenes(BaseTemporal):
    def test_extensiones_de_imagen_registradas(self) -> None:
        for extension in (".png", ".jpg", ".webp", ".tif"):
            with self.subTest(extension=extension):
                with self.assertRaises(ValueError) as contexto:
                    lector.leer(self.base / f"x{extension}")
                # Registrada: el error es de archivo faltante, no de formato.
                self.assertIn("no existe", str(contexto.exception))

    def test_formato_no_soportado_sigue_fallando(self) -> None:
        ruta = self.base / "x.exe"
        ruta.write_bytes(b"contenido")
        with self.assertRaises(ValueError) as contexto:
            lector.leer(ruta)
        self.assertIn("no soportado", str(contexto.exception))

    def test_imagen_sin_ocr_da_error_accionable(self) -> None:
        try:
            import pytesseract  # noqa: F401
        except ImportError:
            pytesseract = None  # type: ignore[assignment]

        if pytesseract is not None:
            self.skipTest("con OCR instalado este caso lo cubre el aviso de imagen vacía")

        ruta = self.base / "escaneo.png"
        ruta.write_bytes(b"no es una imagen de verdad")

        with self.assertRaises(ValueError) as contexto:
            lector.leer(ruta)
        self.assertIn("OCR", str(contexto.exception))


if __name__ == "__main__":
    unittest.main()
