#!/usr/bin/env python3
"""Valida la zona de datos del usuario contra los contratos de herramientas/.

El contrato de cada archivo vive en ``herramientas/contratos/``:

* la cabecera del ``*.example`` declara las columnas obligatorias;
* en ``entidad.csv`` la primera columna declara las claves obligatorias.

La ruta real se deriva por convención::

    herramientas/contratos/organizacion/entidad.csv.example
        -> usuario/datos/organizacion/entidad.csv

Controles:

1. Existencia del archivo real declarado por un contrato.
2. Coincidencia de columnas entre el contrato y el archivo real.
3. Claves obligatorias presentes en ``entidad.csv``.
4. Integridad referencial ``tarifas.codigo_servicio`` -> ``servicios.codigo``.
5. Formato de fechas ``AAAA-MM-DD`` en columnas de vigencia y claves de fecha.
6. Celdas ``PENDIENTE`` y tablas sin filas (advertencias).

Este script **sólo lee**. No corrige, no completa ni escribe en la zona del usuario.

Sólo usa la biblioteca estándar.

Uso:
    python herramientas/scripts/validar_datos.py
    python herramientas/scripts/validar_datos.py --estricto

Salida: ``0`` sin errores, ``1`` con errores. Con ``--estricto`` cualquier
``PENDIENTE`` pendiente también es error.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace as ws  # noqa: E402

RAIZ = ws.RAIZ
DIR_CONTRATOS = RAIZ / "herramientas" / "contratos"

MARCA_PENDIENTE = "PENDIENTE"
PATRON_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Claves de entidad.csv cuyo valor debe ser una fecha.
CLAVES_FECHA = frozenset({"inicio_actividades", "actualizado"})

# Integridad referencial: (archivo real, columna foránea, archivo real destino, columna clave)
# Las rutas son relativas a la carpeta de datos del espacio de trabajo.
INTEGRIDAD = (
    (
        "tablas/tarifas.csv",
        "codigo_servicio",
        "tablas/servicios.csv",
        "codigo",
    ),
)


def leer_tabla(ruta: Path) -> tuple[list[str], list[list[str]]]:
    """Devuelve (cabecera, filas) de un CSV, ignorando filas completamente vacías."""
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        filas = [fila for fila in csv.reader(archivo) if any(celda.strip() for celda in fila)]
    if not filas:
        return [], []
    return [c.strip() for c in filas[0]], filas[1:]


def es_fecha(valor: str) -> bool:
    if not PATRON_FECHA.match(valor):
        return False
    try:
        anio, mes, dia = (int(parte) for parte in valor.split("-"))
    except ValueError:
        return False
    if not 1 <= mes <= 12 or not 1 <= dia <= 31:
        return False
    return anio >= 1900


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Valida la zona de datos del usuario contra sus contratos."
    )
    parser.add_argument(
        "--estricto",
        action="store_true",
        help="trata cualquier valor PENDIENTE como error",
    )
    ws.agregar_argumento(parser)
    args = parser.parse_args(argv)
    espacio = ws.resolver(args.workspace)
    dir_datos = ws.datos(espacio)

    errores: list[str] = []
    advertencias: list[str] = []

    def error(mensaje: str) -> None:
        errores.append(mensaje)

    def advertencia(mensaje: str) -> None:
        advertencias.append(mensaje)

    contratos = sorted(DIR_CONTRATOS.glob("**/*.example"))
    if not contratos:
        error("no se encontró ningún contrato *.example en herramientas/contratos/")
        contratos = []

    tablas: dict[str, tuple[list[str], list[list[str]]]] = {}
    pendientes_totales = 0

    for contrato in contratos:
        relativa_contrato = contrato.relative_to(DIR_CONTRATOS)
        real = dir_datos / relativa_contrato.with_suffix("")
        clave_datos = relativa_contrato.with_suffix("").as_posix()
        relativa_real = ws.mostrar(real, espacio)
        contrato_relativo = contrato.relative_to(RAIZ).as_posix()

        if not real.exists():
            error(
                f"{relativa_real}: falta el archivo real — "
                "ejecutá: python herramientas/scripts/init_local.py"
            )
            continue

        cabecera_contrato, _ = leer_tabla(contrato)
        cabecera_real, filas = leer_tabla(real)
        tablas[clave_datos] = (cabecera_real, filas)

        if not cabecera_contrato:
            error(f"{contrato_relativo}: el contrato no tiene cabecera")
            continue

        if cabecera_real != cabecera_contrato:
            faltan = [c for c in cabecera_contrato if c not in cabecera_real]
            sobran = [c for c in cabecera_real if c not in cabecera_contrato]
            detalle = []
            if faltan:
                detalle.append(f"faltan: {', '.join(faltan)}")
            if sobran:
                detalle.append(f"sobran: {', '.join(sobran)}")
            error(
                f"{relativa_real}: las columnas no coinciden con {contrato_relativo}"
                + (f" ({'; '.join(detalle)})" if detalle else "")
            )
            continue

        ancho = len(cabecera_real)
        for numero, fila in enumerate(filas, start=2):
            if len(fila) != ancho:
                error(f"{relativa_real}:{numero}: se esperaban {ancho} columnas y hay {len(fila)}")
                continue
            for columna, valor in zip(cabecera_real, fila):
                limpio = valor.strip()
                if limpio.upper() == MARCA_PENDIENTE:
                    pendientes_totales += 1
                    if args.estricto or pendientes_totales <= 5:
                        ubicacion = f"{relativa_real}:{numero} ({columna})"
                        if args.estricto:
                            error(f"{ubicacion}: valor PENDIENTE sin completar")
                        else:
                            advertencia(f"{ubicacion}: valor PENDIENTE sin completar")
                elif columna.startswith("vigencia_") or columna.startswith("fecha"):
                    if limpio and not es_fecha(limpio):
                        error(
                            f"{relativa_real}:{numero} ({columna}): fecha inválida '{limpio}',"
                            " se espera AAAA-MM-DD"
                        )

        if not filas and relativa_real != "usuario/datos/organizacion/entidad.csv":
            advertencia(f"{relativa_real}: la tabla no tiene filas")

    # entidad.csv: claves obligatorias y formato de fechas por clave
    ruta_entidad = "usuario/datos/organizacion/entidad.csv"
    entidad = tablas.get(ruta_entidad)
    contrato_entidad = DIR_CONTRATOS / "organizacion" / "entidad.csv.example"
    if entidad is not None and contrato_entidad.exists():
        cabecera, filas = entidad
        if cabecera:
            clave_idx = 0
            valor_idx = cabecera.index("valor") if "valor" in cabecera else 1
            claves_contrato = [
                fila[clave_idx].strip()
                for fila in leer_tabla(contrato_entidad)[1]
                if len(fila) > clave_idx and fila[clave_idx].strip()
            ]
            valores = {
                fila[clave_idx].strip(): fila[valor_idx].strip()
                for fila in filas
                if len(fila) > max(clave_idx, valor_idx)
            }
            for clave in claves_contrato:
                if clave not in valores:
                    error(f"{ruta_entidad}: falta la clave obligatoria '{clave}'")
            for clave in sorted(CLAVES_FECHA & valores.keys()):
                valor = valores[clave]
                if valor and valor.upper() != MARCA_PENDIENTE and not es_fecha(valor):
                    error(f"{ruta_entidad}: '{clave}' = '{valor}' no es una fecha AAAA-MM-DD")

    # Integridad referencial
    for archivo, columna, destino, columna_clave in INTEGRIDAD:
        origen_tabla = tablas.get(archivo)
        destino_tabla = tablas.get(destino)
        if not origen_tabla or not destino_tabla:
            continue
        cab_origen, filas_origen = origen_tabla
        cab_destino, filas_destino = destino_tabla
        if columna not in cab_origen or columna_clave not in cab_destino:
            continue
        idx_origen = cab_origen.index(columna)
        idx_destino = cab_destino.index(columna_clave)
        validos = {
            fila[idx_destino].strip()
            for fila in filas_destino
            if len(fila) > idx_destino and fila[idx_destino].strip()
        }
        if not validos:
            continue
        huerfanos = []
        for numero, fila in enumerate(filas_origen, start=2):
            if len(fila) <= idx_origen:
                continue
            valor = fila[idx_origen].strip()
            if valor and valor.upper() != MARCA_PENDIENTE and valor not in validos:
                huerfanos.append(f"{numero}:{valor}")
        if huerfanos:
            error(
                f"{archivo}: '{columna}' apunta a códigos inexistentes en {destino} "
                f"-> {', '.join(huerfanos)}"
            )

    if args.estricto is False and pendientes_totales > 5:
        advertencia(f"... y {pendientes_totales - 5} celdas PENDIENTE más")

    print("Validación de la zona de datos del usuario")
    print(f"Contratos revisados: {len(contratos)}")
    print(f"Datos del usuario:   {ws.mostrar(dir_datos, espacio)}/")

    if errores:
        print(f"\nErrores ({len(errores)}):")
        for mensaje in errores:
            print(f"  [ERROR] {mensaje}")
    if advertencias:
        print(f"\nAdvertencias ({len(advertencias)}):")
        for mensaje in advertencias:
            print(f"  [AVISO] {mensaje}")

    if errores:
        print("\nResultado: FUENTE DE DATOS INVÁLIDA — no se debe redactar con estos datos.")
        return 1

    if advertencias:
        print("\nResultado: válida con advertencias. Revisá los PENDIENTE antes de entregar.")
        return 0

    print("\nResultado: fuente de datos válida y completa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
