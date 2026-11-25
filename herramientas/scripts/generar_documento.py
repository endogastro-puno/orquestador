#!/usr/bin/env python3
"""Genera documentos desde una spec declarativa y datos CSV.

Un tipo de documento se describe en ``herramientas/contratos/tipos/<tipo>.json``.
El motor resuelve los placeholders, expande las tablas y los bloques repetidos,
calcula el índice y delega el renderizado en ``renderizar_docx.js``.

Reglas que no se negocian:

* Los datos salen de ``usuario/datos/`` (o de un directorio explícito con
  ``--datos``). Nunca se inventan ni se completan valores ``PENDIENTE``.
* Este archivo no contiene ningún dato de empresa.
* La salida se resuelve con ``nuevo_entregable.resolver``: nunca sobrescribe.
* Si el usuario tiene un generador propio en ``usuario/generadores/`` que
  declara el tipo, el motor resuelve el contenido y se lo entrega para que
  aplique su formato. Si no hay generador propio, se usa el renderizador
  genérico. Ver ``herramientas/docs/contrato-generador.md``.

Uso::

    python herramientas/scripts/generar_documento.py --tipo plan-operativo
    python herramientas/scripts/generar_documento.py --tipo manual \\
        --datos ruta/a/datos --salida ruta/entregable.docx --json
    python herramientas/scripts/generar_documento.py --tipo informe \\
        --sin-generador
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
DIR_SPECS = RAIZ / "herramientas" / "contratos" / "tipos"
RENDERIZADOR = RAIZ / "herramientas" / "scripts" / "renderizar_docx.js"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generadores_usuario as gu  # noqa: E402
from nuevo_entregable import resolver  # noqa: E402

PLACEHOLDER = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")
PENDIENTE = "PENDIENTE"
TIEMPO_LIMITE = 120


def cargar_spec(tipo: str) -> dict[str, Any]:
    """Carga y valida la spec declarativa de un tipo."""
    clave = tipo.strip().lower()
    ruta = DIR_SPECS / f"{clave}.json"
    if not ruta.is_file():
        raise ValueError(f"tipo desconocido '{tipo}': no existe {ruta.relative_to(RAIZ).as_posix()}")
    with ruta.open("r", encoding="utf-8-sig") as archivo:
        spec = json.load(archivo)
    if spec.get("tipo") != clave:
        raise ValueError(f"{ruta.name}: el campo 'tipo' debe ser '{clave}'")
    for obligatorio in ("formato", "datos", "bloques"):
        if obligatorio not in spec:
            raise ValueError(f"{ruta.name}: falta el campo obligatorio '{obligatorio}'")
    return spec


def leer_tabla(ruta: Path) -> dict[str, Any]:
    """Lee un CSV con la misma convención que ``validar_datos.py``."""
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        filas = [fila for fila in csv.reader(archivo) if any(c.strip() for c in fila)]
    if not filas:
        return {"cabecera": [], "filas": []}
    return {"cabecera": [c.strip() for c in filas[0]], "filas": filas[1:]}


def leer_datos(spec: dict[str, Any], directorio: Path) -> dict[str, dict[str, Any]]:
    """Carga todos los CSV declarados por la spec desde ``directorio``."""
    datos: dict[str, dict[str, Any]] = {}
    for nombre, relativa in spec["datos"].items():
        ruta = directorio / relativa
        if not ruta.is_file():
            raise ValueError(
                f"falta el archivo de datos '{relativa}' en {directorio}. "
                "El agente no crea ni completa archivos en usuario/datos/."
            )
        datos[nombre] = leer_tabla(ruta)
    return datos


def _mapa(tabla: dict[str, Any]) -> dict[str, str]:
    """Convierte un CSV en mapa campo -> valor.

    Los archivos de organización son de clave/valor (una fila por campo); el
    resto son tablas cuya primera fila aporta el contexto por columna.
    """
    cabecera, filas = tabla["cabecera"], tabla["filas"]
    if not filas:
        return {}
    if cabecera[:2] == ["clave", "valor"]:
        return {fila[0].strip(): fila[1].strip() for fila in filas if len(fila) >= 2}
    return {clave: valor.strip() for clave, valor in zip(cabecera, filas[0])}


def resolver_texto(
    texto: str,
    datos: dict[str, dict[str, Any]],
    constantes: dict[str, str],
    fila: dict[str, str] | None = None,
) -> str:
    """Resuelve ``{{nombre.clave}}`` y ``{{campo}}`` sin dejar marcadores."""

    def reemplazar(coincidencia: re.Match[str]) -> str:
        clave = coincidencia.group(1)
        if clave in constantes:
            return str(constantes[clave])
        if "." in clave:
            nombre, campo = clave.split(".", 1)
            if nombre in constantes:
                valor = str(constantes[nombre])
            else:
                tabla = datos.get(nombre)
                if tabla is None:
                    raise ValueError(f"placeholder '{clave}': no existe la fuente '{nombre}'")
                plano = _mapa(tabla)
                if campo not in plano:
                    raise ValueError(f"placeholder '{clave}': campo '{campo}' no encontrado")
                valor = plano[campo]
        else:
            if fila is None or clave not in fila:
                raise ValueError(f"placeholder '{clave}': campo no disponible en este contexto")
            valor = fila[clave]
        if PENDIENTE in valor.upper():
            raise ValueError(f"placeholder '{clave}': valor PENDIENTE sin completar")
        return valor

    return PLACEHOLDER.sub(reemplazar, texto)


def _resolver_recursivo(
    valor: Any,
    datos: dict[str, dict[str, Any]],
    constantes: dict[str, str],
    fila: dict[str, str] | None,
) -> Any:
    if isinstance(valor, str):
        return resolver_texto(valor, datos, constantes, fila)
    if isinstance(valor, list):
        return [_resolver_recursivo(v, datos, constantes, fila) for v in valor]
    if isinstance(valor, dict):
        return {k: _resolver_recursivo(v, datos, constantes, fila) for k, v in valor.items()}
    return valor


def _filas_tabla(bloque: dict[str, Any], datos: dict[str, dict[str, Any]]) -> list[list[str]]:
    fuente = bloque.get("fuente")
    if not fuente:
        return bloque.get("filas", [])
    tabla = datos.get(fuente)
    if tabla is None:
        raise ValueError(f"tabla con fuente desconocida '{fuente}'")
    columnas = bloque.get("columnas")
    if not columnas:
        raise ValueError(f"tabla con fuente '{fuente}' no declara 'columnas'")
    indices = []
    for columna in columnas:
        if columna not in tabla["cabecera"]:
            raise ValueError(f"tabla '{fuente}': la columna '{columna}' no existe")
        indices.append(tabla["cabecera"].index(columna))
    filas = [
        [fila[i] if i < len(fila) else "" for i in indices]
        for fila in tabla["filas"]
    ]
    for fila in filas:
        for celda in fila:
            if PENDIENTE in celda.upper():
                raise ValueError(
                    f"tabla '{fuente}': hay un valor PENDIENTE sin completar; "
                    "el agente no lo completa, lo completa el usuario"
                )
    totales = bloque.get("totales")
    if totales:
        cabecera = tabla["cabecera"]
        fila_total = ["TOTAL"] + [""] * (len(columnas) - 1)
        for campo in totales:
            if campo not in columnas:
                raise ValueError(f"totales: '{campo}' no está entre las columnas")
            posicion = columnas.index(campo)
            indice_campo = cabecera.index(campo)
            suma = 0.0
            for numero, fila in enumerate(tabla["filas"], start=2):
                if indice_campo >= len(fila):
                    raise ValueError(
                        f"tabla '{fuente}':{numero}: faltan columnas para sumar '{campo}'"
                    )
                crudo = fila[indice_campo].strip().replace(",", "")
                try:
                    suma += float(crudo)
                except ValueError:
                    raise ValueError(
                        f"totales: '{crudo}' no es numérico en '{campo}' "
                        f"({fuente}:{numero})"
                    ) from None
            fila_total[posicion] = f"{suma:,.2f}"
        filas.append(fila_total)
    return filas


def _finalizar_tabla(
    resuelto: dict[str, Any],
    bloque: dict[str, Any],
    datos: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Completa una tabla con fuente CSV y quita las claves de expansión."""
    if resuelto.get("tipo") == "tabla" and bloque.get("fuente"):
        resuelto["filas"] = _filas_tabla(bloque, datos)
        for clave in ("fuente", "columnas", "totales"):
            resuelto.pop(clave, None)
    return resuelto


def _lista_desde(bloque: dict[str, Any], valor: str) -> dict[str, Any]:
    """Convierte un campo separado por ``|`` en una lista."""
    separador = bloque.get("separador", "|")
    return {
        "tipo": "lista",
        "items": [parte.strip() for parte in valor.split(separador) if parte.strip()],
        "numerada": bloque.get("numerada", False),
    }


def expandir(
    bloques: list[dict[str, Any]],
    datos: dict[str, dict[str, Any]],
    constantes: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Aplana los bloques: resuelve placeholders, tablas, listas y repeticiones."""
    constantes = constantes or {}
    resultado: list[dict[str, Any]] = []

    for bloque in bloques:
        tipo = bloque.get("tipo")
        if tipo == "repetir":
            fuente = bloque["fuente"]
            tabla = datos.get(fuente)
            if tabla is None:
                raise ValueError(f"repetir: fuente desconocida '{fuente}'")
            if not tabla["filas"]:
                raise ValueError(
                    f"repetir: '{fuente}' no tiene filas; el documento quedaría sin "
                    "las secciones que dependen de esos datos"
                )
            for indice, fila_cruda in enumerate(tabla["filas"]):
                fila = {
                    clave: valor.strip()
                    for clave, valor in zip(tabla["cabecera"], fila_cruda)
                }
                if indice and bloque.get("por_pagina", True):
                    resultado.append({"tipo": "pagina"})
                resultado.extend(
                    _expandir_con_fila(bloque["bloques"], datos, constantes, fila)
                )
            continue

        resuelto = _resolver_recursivo(bloque, datos, constantes, None)
        if resuelto.get("tipo") == "lista" and "desde" in resuelto:
            campo = resuelto["desde"]
            plano = _mapa(datos.get("entidad", {"cabecera": [], "filas": []}))
            valor = str(constantes.get(campo, plano.get(campo, "")))
            resuelto = _lista_desde(bloque, valor)
        resultado.append(_finalizar_tabla(resuelto, bloque, datos))
    return resultado


def _expandir_con_fila(
    bloques: list[dict[str, Any]],
    datos: dict[str, dict[str, Any]],
    constantes: dict[str, str],
    fila: dict[str, str],
) -> list[dict[str, Any]]:
    resultado: list[dict[str, Any]] = []
    for bloque in bloques:
        if bloque.get("tipo") == "lista" and "desde" in bloque:
            resultado.append(_lista_desde(bloque, fila.get(bloque["desde"], "")))
            continue
        resuelto = _resolver_recursivo(bloque, datos, constantes, fila)
        resultado.append(_finalizar_tabla(resuelto, bloque, datos))
    return resultado


def calcular_indice(bloques: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calcula los números de página de las entradas marcadas con ``indice``."""
    pagina = 1
    entradas: list[dict[str, Any]] = []
    for bloque in bloques:
        if bloque.get("tipo") == "pagina":
            pagina += 1
        elif bloque.get("indice") is True and bloque.get("texto"):
            entradas.append({"texto": bloque["texto"], "pagina": pagina})
    return entradas


def construir_payload(
    spec: dict[str, Any],
    datos: dict[str, dict[str, Any]],
    indice: list[dict[str, Any]],
    bloques: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Ensambla el JSON que consume el renderizador, sin rutas absolutas."""
    if bloques is None:
        bloques = expandir(spec["bloques"], datos, spec.get("constantes", {}))
    return {
        "tipo": spec["tipo"],
        "titulo": spec.get("titulo", spec["tipo"]),
        "formato": spec["formato"],
        "bloques": bloques,
        "indice": indice,
        "pie": f"{spec.get('titulo', spec['tipo'])} · v1.0",
    }


def _nombre_entregable(spec: dict[str, Any], datos: dict[str, dict[str, Any]]) -> str:
    plantilla = spec.get("nombre_entregable", spec["titulo"])
    plano = _mapa(datos.get("entidad", {"cabecera": [], "filas": []}))
    empresa = plano.get("nombre_comercial") or plano.get("razon_social") or spec["titulo"]
    return plantilla.replace("{empresa}", empresa)


def _validar_salida(ruta: Path) -> Path:
    """Exige una ruta nueva dentro de usuario/entregables/ y nunca sobrescribe."""
    entregables = (RAIZ / "usuario" / "entregables").resolve()
    destino = ruta.resolve()
    try:
        destino.relative_to(entregables)
    except ValueError:
        raise ValueError(
            f"--salida debe quedar dentro de usuario/entregables/: {destino}"
        ) from None
    if destino.exists():
        raise ValueError(
            f"--salida ya existe y no se sobrescribe: {destino.name}. "
            "Elegí otro nombre o dejá que el motor resuelva la ruta."
        )
    return destino


def _anio(fecha: str | None) -> str:
    """Año del periodo, derivado de --fecha o del día actual."""
    if fecha and re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        return fecha[:4]
    from datetime import date

    return str(date.today().year)


def _elegir_generador(args: argparse.Namespace, tipo: str) -> gu.Generador | None:
    """Decide si el documento se produce con un generador propio del usuario."""
    if getattr(args, "sin_generador", False):
        return None
    if args.generador:
        generador = gu.cargar(Path(args.generador))
        if not (generador.cubre(tipo) or generador.cubre_todo()):
            declarados = ", ".join(generador.tipos) or "ninguno"
            raise ValueError(
                f"el generador '{generador.nombre}' no declara el tipo '{tipo}' "
                f"(declara: {declarados})"
            )
        return generador
    return gu.seleccionar(gu.descubrir(RAIZ / "usuario" / "generadores"), tipo)


def _renderizar_con_docx(payload: dict[str, Any], salida: Path) -> None:
    """Renderiza el payload con el renderizador genérico (Node + docx)."""
    if not RENDERIZADOR.is_file():
        raise ValueError(f"falta el renderizador {RENDERIZADOR.relative_to(RAIZ).as_posix()}")
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".json", delete=False
    ) as temporal:
        json.dump(payload, temporal, ensure_ascii=False)
        ruta_payload = temporal.name

    entorno = os.environ.copy()
    nodos = RAIZ / "node_modules"
    entorno["NODE_PATH"] = str(nodos) + (
        os.pathsep + entorno["NODE_PATH"] if entorno.get("NODE_PATH") else ""
    )
    try:
        resultado = subprocess.run(
            ["node", str(RENDERIZADOR), ruta_payload, str(salida)],
            cwd=RAIZ,
            env=entorno,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=TIEMPO_LIMITE,
        )
    finally:
        Path(ruta_payload).unlink(missing_ok=True)

    if resultado.returncode != 0:
        raise ValueError(f"renderizador falló: {resultado.stderr.strip() or resultado.stdout.strip()}")
    if not salida.is_file() or salida.stat().st_size == 0:
        raise ValueError(f"el renderizador no produjo un archivo válido en {salida.name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--tipo", required=True, help="nombre de la spec en herramientas/contratos/tipos/")
    parser.add_argument("--datos", help="directorio con la estructura de usuario/datos/")
    parser.add_argument("--nombre", help="override del nombre del entregable")
    parser.add_argument("--fecha", help="fecha AAAA-MM-DD (por defecto, hoy)")
    parser.add_argument("--salida", help="ruta nueva dentro de usuario/entregables/")
    parser.add_argument(
        "--generador",
        help="carpeta del generador propio del usuario (por defecto: el que declare el tipo)",
    )
    parser.add_argument(
        "--sin-generador",
        action="store_true",
        help="ignora los generadores propios del usuario y usa el renderizador genérico",
    )
    parser.add_argument("--json", action="store_true", help="resultado como JSON")
    args = parser.parse_args(argv)

    try:
        spec = cargar_spec(args.tipo)
        directorio = Path(args.datos).resolve() if args.datos else RAIZ / "usuario" / "datos"
        datos = leer_datos(spec, directorio)
        constantes = dict(spec.get("constantes", {}))
        constantes.setdefault("anio", _anio(args.fecha))
        bloques = expandir(spec["bloques"], datos, constantes)
        indice = calcular_indice(bloques)

        if args.salida:
            salida = _validar_salida(Path(args.salida))
        else:
            nombre = args.nombre or _nombre_entregable(spec, datos)
            salida = resolver("word", nombre, args.fecha)
        salida.parent.mkdir(parents=True, exist_ok=True)

        generador = _elegir_generador(args, spec["tipo"])
        if generador is not None:
            payload = gu.construir_payload(
                spec,
                datos,
                bloques,
                indice,
                salida.relative_to(RAIZ).as_posix(),
                constantes,
            )
            gu.ejecutar(generador, payload, raiz=RAIZ)
            motor_usado = "generador-usuario"
            generador_usado: str | None = generador.nombre
        else:
            payload = construir_payload(spec, datos, indice, bloques)
            _renderizar_con_docx(payload, salida)
            motor_usado = "renderizador-docx"
            generador_usado = None
    except (
        ValueError,
        IndexError,
        KeyError,
        OSError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as error:
        if args.json:
            print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "tipo": spec["tipo"],
                    "motor": motor_usado,
                    "generador": generador_usado,
                    "salida": str(salida),
                    "bytes": salida.stat().st_size,
                    "paginas_indexadas": len(indice),
                    "entradas": indice,
                },
                ensure_ascii=False,
            )
        )
    else:
        detalle = f" · generador '{generador_usado}'" if generador_usado else ""
        print(
            f"OK {salida.relative_to(RAIZ).as_posix()} "
            f"({salida.stat().st_size} bytes){detalle}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
