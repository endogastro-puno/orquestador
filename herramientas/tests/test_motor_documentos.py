"""Regresiones del motor declarativo de documentos.

Sólo biblioteca estándar. Se ejecuta con:

    python -m unittest discover -s herramientas/tests -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "herramientas" / "scripts"))

import generar_documento as motor  # noqa: E402  (import tras ajustar sys.path)


class TestCargaDeSpecs(unittest.TestCase):
    def test_spec_plan_operativo_existe_y_es_valida(self) -> None:
        spec = motor.cargar_spec("plan-operativo")

        self.assertEqual(spec["tipo"], "plan-operativo")
        self.assertEqual(spec["formato"], "docx")
        self.assertIn("entidad", spec["datos"])
        self.assertIn("actividades", spec["datos"])
        self.assertIn("partidas", spec["datos"])
        self.assertTrue(spec["bloques"])

    def test_spec_manual_existe_y_tiene_fichas_por_puesto(self) -> None:
        spec = motor.cargar_spec("manual")

        self.assertEqual(spec["tipo"], "manual")
        repetir = [b for b in spec["bloques"] if b.get("tipo") == "repetir"]
        self.assertEqual(len(repetir), 1)
        self.assertEqual(repetir[0]["fuente"], "puestos")

    def test_tipo_desconocido_falla_con_mensaje_claro(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            motor.cargar_spec("no-existe")
        self.assertIn("no-existe", str(ctx.exception))


class TestExpansionYPlaceholders(unittest.TestCase):
    def test_placeholders_se_resuelven_desde_los_datos(self) -> None:
        datos = {
            "entidad": {
                "cabecera": ["razon_social", "ruc"],
                "filas": [["KILOCLINIC S.A.C.", "20609988776"]],
            }
        }
        bloques = [{"tipo": "parrafo", "texto": "{{entidad.razon_social}} — RUC {{entidad.ruc}}"}]

        resultado = motor.expandir(bloques, datos)

        self.assertEqual(resultado[0]["texto"], "KILOCLINIC S.A.C. — RUC 20609988776")

    def test_repetir_expande_una_ficha_por_fila_con_pagina_entre_ellas(self) -> None:
        datos = {
            "puestos": {
                "cabecera": ["codigo_puesto", "denominacion"],
                "filas": [
                    ["DIR-001", "Director Médico"],
                    ["ADM-001", "Administrador"],
                ],
            }
        }
        bloques = [
            {
                "tipo": "repetir",
                "fuente": "puestos",
                "por_pagina": True,
                "bloques": [
                    {"tipo": "titulo", "nivel": 2, "texto": "{{codigo_puesto}} — {{denominacion}}", "indice": True}
                ],
            }
        ]

        resultado = motor.expandir(bloques, datos)
        titulos = [b for b in resultado if b.get("tipo") == "titulo"]

        self.assertEqual(len(titulos), 2)
        self.assertEqual(titulos[0]["texto"], "DIR-001 — Director Médico")
        self.assertEqual(titulos[1]["texto"], "ADM-001 — Administrador")
        self.assertEqual(resultado[1]["tipo"], "pagina")

    def test_tabla_estatica_tambien_resuelve_placeholders(self) -> None:
        bloques = [
            {
                "tipo": "tabla",
                "encabezado": ["Campo", "Valor"],
                "filas": [["Periodo", "Enero a diciembre de {{anio}}"]],
                "anchos": [3000, 6026],
            }
        ]

        resultado = motor.expandir(bloques, {}, {"anio": "2026"})

        self.assertEqual(resultado[0]["filas"][0][1], "Enero a diciembre de 2026")
        self.assertNotIn("{{", json.dumps(resultado, ensure_ascii=False))

    def test_placeholder_sin_datos_falla_en_lugar_de_quedar_visible(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            motor.expandir([{"tipo": "parrafo", "texto": "{{entidad.razon_social}}"}], {})
        self.assertIn("entidad.razon_social", str(ctx.exception))

    def test_pendiente_nunca_llega_al_documento(self) -> None:
        datos = {
            "entidad": {
                "cabecera": ["razon_social"],
                "filas": [["PENDIENTE"]],
            }
        }
        with self.assertRaises(ValueError) as ctx:
            motor.expandir([{"tipo": "parrafo", "texto": "{{entidad.razon_social}}"}], datos)
        self.assertIn("PENDIENTE", str(ctx.exception))


class TestIndiceDeterminista(unittest.TestCase):
    def test_paginas_se_calculan_desde_los_saltos(self) -> None:
        bloques = [
            {"tipo": "portada"},
            {"tipo": "pagina"},
            {"tipo": "tabla"},
            {"tipo": "pagina"},
            {"tipo": "indice"},
            {"tipo": "pagina"},
            {"tipo": "titulo", "nivel": 1, "texto": "I. Objetivo", "indice": True},
            {"tipo": "titulo", "nivel": 1, "texto": "II. Alcance", "indice": True},
        ]

        entradas = motor.calcular_indice(bloques)

        self.assertEqual(
            entradas,
            [
                {"texto": "I. Objetivo", "pagina": 4},
                {"texto": "II. Alcance", "pagina": 4},
            ],
        )

    def test_solo_se_indexan_bloques_marcados(self) -> None:
        bloques = [
            {"tipo": "titulo", "nivel": 1, "texto": "No indexado"},
            {"tipo": "titulo", "nivel": 2, "texto": "Tampoco", "indice": False},
            {"tipo": "titulo", "nivel": 1, "texto": "Sí indexado", "indice": True},
        ]
        self.assertEqual(motor.calcular_indice(bloques), [{"texto": "Sí indexado", "pagina": 1}])


class TestPayloadSinFugas(unittest.TestCase):
    def test_payload_no_contiene_rutas_absolutas(self) -> None:
        spec = {
            "tipo": "prueba",
            "titulo": "Prueba",
            "formato": "docx",
            "constantes": {},
            "bloques": [{"tipo": "parrafo", "texto": "sin placeholders"}],
        }
        payload = motor.construir_payload(spec, {}, [])

        serializado = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn(str(RAIZ), serializado)
        self.assertNotIn("C:\\", serializado)


class TestSalidaSinSobrescribir(unittest.TestCase):
    def test_nuevo_entregable_agrega_v2(self) -> None:
        from nuevo_entregable import resolver

        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            primera = resolver("word", "Plan Operativo KILOCLINIC", "2026-11-25", base=base)
            primera.parent.mkdir(parents=True, exist_ok=True)
            primera.write_text("x", encoding="utf-8")
            segunda = resolver("word", "Plan Operativo KILOCLINIC", "2026-11-25", base=base)

        self.assertEqual(segunda.name, "2026-11-25_plan-operativo-kiloclinic-v2.docx")


class TestProteccionDeSalida(unittest.TestCase):
    def test_salida_existente_se_rechaza_sin_sobrescribir(self) -> None:
        destino = RAIZ / "usuario" / "entregables" / "word" / "_prueba_no_sobrescribir.docx"
        destino.write_text("original", encoding="utf-8")
        try:
            with self.assertRaises(ValueError) as ctx:
                motor._validar_salida(destino)
            self.assertIn("no se sobrescribe", str(ctx.exception))
            self.assertEqual(destino.read_text(encoding="utf-8"), "original")
        finally:
            destino.unlink(missing_ok=True)

    def test_salida_fuera_de_entregables_se_rechaza(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            with self.assertRaises(ValueError) as ctx:
                motor._validar_salida(Path(temporal) / "x.docx")
        self.assertIn("usuario/entregables", str(ctx.exception))


class TestDatosInvalidos(unittest.TestCase):
    def test_totales_con_fila_corta_es_valueerror_no_indexerror(self) -> None:
        datos = {
            "partidas": {
                "cabecera": ["codigo", "presupuestado"],
                "filas": [["P-001"], ["P-002", "10.00"]],
            }
        }
        bloque = {
            "tipo": "tabla",
            "fuente": "partidas",
            "columnas": ["codigo", "presupuestado"],
            "totales": ["presupuestado"],
        }
        with self.assertRaises(ValueError) as ctx:
            motor._filas_tabla(bloque, datos)
        self.assertIn("faltan columnas", str(ctx.exception))

    def test_pendiente_en_tabla_csv_falla(self) -> None:
        datos = {
            "actividades": {
                "cabecera": ["codigo", "actividad"],
                "filas": [["ACT-001", "PENDIENTE"]],
            }
        }
        bloque = {
            "tipo": "tabla",
            "fuente": "actividades",
            "columnas": ["codigo", "actividad"],
        }
        with self.assertRaises(ValueError) as ctx:
            motor._filas_tabla(bloque, datos)
        self.assertIn("PENDIENTE", str(ctx.exception))

    def test_repetir_sin_filas_falla(self) -> None:
        datos = {"puestos": {"cabecera": ["codigo_puesto"], "filas": []}}
        with self.assertRaises(ValueError) as ctx:
            motor.expandir([{"tipo": "repetir", "fuente": "puestos", "bloques": []}], datos)
        self.assertIn("no tiene filas", str(ctx.exception))


class TestPeriodo(unittest.TestCase):
    def test_anio_sale_de_la_fecha_pedida(self) -> None:
        self.assertEqual(motor._anio("2026-11-25"), "2026")

    def test_anio_sin_fecha_no_falla(self) -> None:
        self.assertRegex(motor._anio(None), r"^\d{4}$")


if __name__ == "__main__":
    unittest.main()
