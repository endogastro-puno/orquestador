#!/usr/bin/env python3
"""Pruebas de regresión de los scripts de ``herramientas/``.

Sólo biblioteca estándar: no hace falta instalar nada para correrlas.

    python -m unittest discover -s herramientas/tests -v

Cubren las dos reglas que más fácil se rompen sin que nadie lo note:

* el instalador no toca Node.js cuando lo administra NVM;
* los requisitos opcionales no disparan una instalación de pip.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPTS = RAIZ / "herramientas" / "scripts"

# Los scripts importan módulos que viven a su lado (entorno_windows). Al correrlos
# como script Python ya agrega esa carpeta; al importarlos por ruta hay que hacerlo.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def cargar(nombre: str):
    """Importa un script por ruta, sin depender del nombre del directorio."""
    ruta = SCRIPTS / f"{nombre}.py"
    especificacion = importlib.util.spec_from_file_location(f"script_{nombre}", ruta)
    if especificacion is None or especificacion.loader is None:  # pragma: no cover
        raise unittest.SkipTest(f"no se pudo cargar {ruta}")
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


class DeteccionDeNvm(unittest.TestCase):
    def setUp(self) -> None:
        self.modulo = cargar("instalar_todo")

    def test_devuelve_un_booleano(self) -> None:
        self.assertIsInstance(self.modulo.nvm_presente(), bool)

    def test_sin_variables_de_nvm_no_explota(self) -> None:
        guardadas = {
            clave: os.environ.pop(clave)
            for clave in ("NVM_HOME", "NVM_SYMLINK")
            if clave in os.environ
        }
        try:
            self.assertIsInstance(self.modulo.nvm_presente(), bool)
        finally:
            os.environ.update(guardadas)

    def test_nvm_home_alcanza_para_detectarlo(self) -> None:
        if sys.platform != "win32":
            self.skipTest("NVM for Windows sólo existe en Windows")
        guardado = os.environ.get("NVM_HOME")
        os.environ["NVM_HOME"] = r"C:\cualquier\carpeta\nvm"
        try:
            self.assertTrue(self.modulo.nvm_presente())
        finally:
            if guardado is None:
                os.environ.pop("NVM_HOME", None)
            else:
                os.environ["NVM_HOME"] = guardado


class RefrescoDePath(unittest.TestCase):
    """``verificar_entorno.py`` debe ver lo que ``instalar_todo.py`` acaba de instalar."""

    @staticmethod
    def _entradas() -> list[str]:
        return [
            entrada.strip().lower()
            for entrada in os.environ.get("PATH", "").split(os.pathsep)
            if entrada.strip()
        ]

    def test_no_vacia_el_path(self) -> None:
        modulo = cargar("entorno_windows")
        antes = os.environ.get("PATH", "")
        modulo.refrescar_path()
        despues = os.environ.get("PATH", "")
        self.assertTrue(despues.strip())
        for entrada in antes.split(os.pathsep):
            if entrada.strip():
                self.assertIn(entrada.strip().lower(), despues.lower())

    def test_no_duplica_entradas(self) -> None:
        modulo = cargar("entorno_windows")
        antes = self._entradas()
        modulo.refrescar_path()
        modulo.refrescar_path()
        despues = self._entradas()

        # El refresco no puede perder entradas ni agregar duplicados. Un PATH
        # heredado puede traer repetidos de antes (pasa en los runners de CI),
        # así que se compara contra el estado inicial, no contra cero.
        self.assertTrue(set(antes) <= set(despues), "el refresco perdió entradas")
        self.assertLessEqual(
            len(despues) - len(set(despues)),
            len(antes) - len(set(antes)),
            "el refresco agregó entradas duplicadas",
        )

    def test_el_verificador_usa_el_refresco(self) -> None:
        fuente = (SCRIPTS / "verificar_entorno.py").read_text(encoding="utf-8")
        self.assertIn("refrescar_path()", fuente)


class RequisitosOpcionales(unittest.TestCase):
    """Un opcional ausente no puede activar ``pip install``."""

    @staticmethod
    def estado(formatos: tuple[str, ...] = (), opcionales: tuple[str, ...] = ()) -> dict:
        return {
            "resultados": {
                "base": {"python": {"ok": True}},
                "formatos": {"xlsx": {clave: {"ok": False} for clave in formatos}},
                "opcionales": {clave: {"ok": False} for clave in opcionales},
            }
        }

    def setUp(self) -> None:
        self.modulo = cargar("instalar_todo")

    def test_opcionales_ausentes_no_piden_pip(self) -> None:
        _, pip, npm, python_malo = self.modulo.faltantes(
            self.estado(opcionales=("cmd:markitdown", "mod:pytesseract"))
        )
        self.assertFalse(pip)
        self.assertFalse(npm)
        self.assertFalse(python_malo)

    def test_opcionales_ausentes_no_listan_programas(self) -> None:
        programas, _, _, _ = self.modulo.faltantes(
            self.estado(opcionales=("cmd:markitdown", "mod:pytesseract"))
        )
        self.assertEqual(programas, [])

    def test_modulo_de_formato_si_pide_pip(self) -> None:
        _, pip, _, _ = self.modulo.faltantes(self.estado(formatos=("mod:openpyxl",)))
        self.assertTrue(pip)

    def test_npm_de_formato_pide_npm(self) -> None:
        _, _, npm, _ = self.modulo.faltantes(self.estado(formatos=("npm:docx",)))
        self.assertTrue(npm)

    def test_python_viejo_se_reporta(self) -> None:
        estado = {"resultados": {"base": {"python": {"ok": False}}}}
        _, _, _, python_malo = self.modulo.faltantes(estado)
        self.assertTrue(python_malo)


class ContratoDelVerificador(unittest.TestCase):
    """``markitdown`` es comodidad, no requisito de Excel."""

    @classmethod
    def setUpClass(cls) -> None:
        resultado = subprocess.run(
            [sys.executable, str(SCRIPTS / "verificar_entorno.py"), "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=RAIZ,
        )
        cls.datos = json.loads(resultado.stdout)

    def test_markitdown_no_bloquea_xlsx(self) -> None:
        requisitos = self.datos["resultados"]["formatos"]["xlsx"]
        self.assertNotIn("cmd:markitdown", requisitos)
        self.assertIn("mod:openpyxl", requisitos)

    def test_markitdown_aparece_como_opcional(self) -> None:
        self.assertIn("cmd:markitdown", self.datos["resultados"]["opcionales"])

    def test_json_tiene_las_tres_secciones(self) -> None:
        for seccion in ("base", "formatos", "opcionales"):
            self.assertIn(seccion, self.datos["resultados"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
