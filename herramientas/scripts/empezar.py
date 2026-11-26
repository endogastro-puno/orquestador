#!/usr/bin/env python3
"""Deja el orquestador listo para usar en un solo comando.

Es la puerta de entrada para quien acaba de clonar el repositorio y no quiere
armar nada a mano: revisa el entorno, instala lo que falta (si se lo pedís),
crea las carpetas de la zona del usuario, copia los contratos de datos y deja
una plantilla base por cada tipo de documento. Todo lo que ya existe se
respeta: nunca sobrescribe, nunca borra y nunca completa un ``PENDIENTE``.

Uso::

    python herramientas/scripts/empezar.py            # pregunta antes de instalar
    python herramientas/scripts/empezar.py --si       # sin preguntar
    python herramientas/scripts/empezar.py --plan     # sólo muestra qué haría
    python herramientas/scripts/empezar.py --workspace D:\\\\clientes\\\\clinica-a

Opciones útiles:

* ``--sin-instalar`` — no toca programas; sólo prepara carpetas, datos y
  plantillas (para cuando el equipo ya está instalado).
* ``--sin-plantillas`` — no crea plantillas base.
* ``--con-ocr`` — al instalar, suma Tesseract y ``pytesseract`` para leer
  escaneados.

Códigos de salida: ``0`` todo listo, ``1`` la estructura quedó preparada pero
falta algo obligatorio del entorno, no se pudo verificar el entorno, o hubo un
error de escritura.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import init_local  # noqa: E402
import instalar_todo  # noqa: E402
import nueva_plantilla as np  # noqa: E402
import plantillas as pl  # noqa: E402
import verificar_entorno as ve  # noqa: E402
import workspace as ws  # noqa: E402


def _verificar() -> dict | None:
    """Corre el verificador en modo JSON y devuelve su estado."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        ve.main(["--json"])
    try:
        return json.loads(buffer.getvalue())
    except json.JSONDecodeError:
        return None


def _faltantes(estado: dict | None) -> tuple[list[str], list[str]]:
    """(obligatorios, opcionales) que faltan según el verificador."""
    if not estado:
        return [], []
    return (
        list(estado.get("faltantes_obligatorios") or []),
        list(estado.get("faltantes_opcionales") or []),
    )


def faltan_carpetas(espacio: Path) -> list[str]:
    """Subcarpetas de la zona del usuario que todavía no existen."""
    return [relativa for relativa in ws.SUBCARPETAS if not (Path(espacio) / relativa).exists()]


def faltan_datos(espacio: Path) -> list[Path]:
    """Contratos que todavía no tienen su archivo real en ``datos/``."""
    faltantes: list[Path] = []
    for contrato in sorted(init_local.DIR_CONTRATOS.glob("**/*.example")):
        relativa = contrato.relative_to(init_local.DIR_CONTRATOS)
        real = Path(espacio) / "datos" / relativa.with_suffix("")
        if not real.exists():
            faltantes.append(real)
    return faltantes


def tipos_sin_plantilla(espacio: Path) -> list[str]:
    """Tipos que no tienen ninguna plantilla propia (no se duplican)."""
    carpeta = pl.carpeta_destino(espacio)
    return [tipo for tipo in sorted(pl.TIPOS) if not any(carpeta.glob(f"{tipo}-*"))]


def crear_plantillas(espacio: Path) -> tuple[list[Path], list[str], list[tuple[str, str]]]:
    """Crea una plantilla base por tipo que no tenga ninguna.

    Devuelve (creadas, tipos que ya tenían plantilla, errores). No duplica:
    si el usuario ya trajo su plantilla de un tipo, ese tipo se respeta.
    """
    creadas: list[Path] = []
    existentes: list[str] = []
    errores: list[tuple[str, str]] = []
    for tipo in sorted(pl.TIPOS):
        carpeta = pl.carpeta_destino(espacio)
        if any(carpeta.glob(f"{tipo}-*")):
            existentes.append(tipo)
            continue
        extension = pl.extensiones_de(tipo)[0]
        try:
            creadas.append(np.crear(tipo, "base", extension, espacio))
        except (ValueError, OSError) as error:
            errores.append((tipo, str(error)))
    return creadas, existentes, errores


def preparar(espacio: Path, con_plantillas: bool = True) -> dict:
    """Crea lo que falte en la zona del usuario. No pisa nada existente."""
    carpetas = init_local.crear_carpetas(espacio)
    datos_creados, datos_respetados = init_local.copiar_contratos(espacio)
    plantillas_creadas: list[Path] = []
    plantillas_existentes: list[str] = []
    plantillas_error: list[tuple[str, str]] = []
    if con_plantillas:
        plantillas_creadas, plantillas_existentes, plantillas_error = crear_plantillas(espacio)
    return {
        "carpetas": carpetas,
        "datos_creados": datos_creados,
        "datos_respetados": datos_respetados,
        "plantillas_creadas": plantillas_creadas,
        "plantillas_existentes": plantillas_existentes,
        "plantillas_error": plantillas_error,
    }


def datos_pendientes(espacio: Path) -> list[Path]:
    """Archivos de datos que todavía tienen ``PENDIENTE`` (no se completan acá)."""
    pendientes: list[Path] = []
    carpeta = Path(espacio) / "datos"
    for archivo in sorted(carpeta.glob("**/*.csv")):
        try:
            if "PENDIENTE" in archivo.read_text(encoding="utf-8-sig"):
                pendientes.append(archivo)
        except OSError:
            continue
    return pendientes


def mostrar_plan(espacio: Path, estado: dict | None) -> int:
    """Muestra qué haría el arranque, sin escribir ni instalar nada."""
    obligatorios, opcionales = _faltantes(estado)
    carpetas = faltan_carpetas(espacio)
    datos = faltan_datos(espacio)
    tipos = tipos_sin_plantilla(espacio)

    print(f"Espacio de trabajo: {ws.mostrar(espacio)}")
    print("Plan de primer arranque (no se escribe nada):\n")

    if estado is None:
        print("  Entorno      no se pudo revisar; corré verificar_entorno.py a mano")
    elif obligatorios:
        print(f"  Entorno      faltan {len(obligatorios)}: {', '.join(obligatorios)}")
    else:
        print("  Entorno      completo")
    if opcionales:
        print(f"  Opcionales   faltan {len(opcionales)}: {', '.join(opcionales)}")

    print(f"  Carpetas     {len(carpetas)} por crear" if carpetas else "  Carpetas     todas ya existen")
    print(f"  Datos        {len(datos)} archivo(s) por copiar" if datos else "  Datos        todos ya existen")
    if tipos:
        print(f"  Plantillas   {len(tipos)} por crear: {', '.join(tipos)}")
    else:
        print("  Plantillas   todos los tipos ya tienen una")

    if not (obligatorios or carpetas or datos or tipos):
        print("\nNada que preparar: el espacio ya estaba completo.")
    else:
        print("\nPara ejecutarlo: python herramientas/scripts/empezar.py --si")
    return 0


def _confirmar(pregunta: str) -> bool:
    try:
        respuesta = input(pregunta).strip().lower()
    except EOFError:
        return False
    return respuesta not in ("n", "no")


def _paso(numero: int, total: int, titulo: str) -> None:
    print(f"\n[{numero}/{total}] {titulo}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--plan", action="store_true", help="sólo muestra qué haría")
    parser.add_argument("--si", action="store_true", help="no pide confirmación para instalar")
    parser.add_argument(
        "--sin-instalar",
        action="store_true",
        help="no instala programas; sólo prepara carpetas, datos y plantillas",
    )
    parser.add_argument(
        "--sin-plantillas",
        action="store_true",
        help="no crea plantillas base",
    )
    parser.add_argument(
        "--con-ocr",
        action="store_true",
        help="al instalar, suma Tesseract y pytesseract (leer escaneados)",
    )
    parser.add_argument("--selftest", action="store_true", help="prueba de humo; no toca nada")
    ws.agregar_argumento(parser)
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    espacio = ws.resolver(args.workspace)
    estado = _verificar()

    if args.plan:
        return mostrar_plan(espacio, estado)

    print("=" * 68)
    print("  PRIMER ARRANQUE DEL ORQUESTADOR DOCUMENTAL")
    print("=" * 68)
    print(f"Repositorio:       {ws.RAIZ}")
    print(f"Espacio de trabajo: {ws.mostrar(espacio)}")

    total = 4
    _paso(1, total, "Revisando el entorno")
    obligatorios, opcionales = _faltantes(estado)
    if estado is None:
        print("  No se pudo revisar el entorno; sigo con la estructura.")
    elif not obligatorios:
        print("  Todo lo obligatorio está instalado.")
    else:
        print(f"  Faltan {len(obligatorios)}: {', '.join(obligatorios)}")
        if args.sin_instalar:
            print("  --sin-instalar: no toco programas. La estructura se prepara igual.")
        elif sys.platform != "win32":
            print("  La instalación automática es para Windows: seguí INSTALACION.md.")
        elif args.si or _confirmar("  ¿Instalo lo que falta ahora? [S/n]: "):
            print()
            codigo = instalar_todo.main(
                ["--si"] + (["--con-ocr"] if args.con_ocr else [])
            )
            if codigo == 0:
                estado = _verificar()
                obligatorios, opcionales = _faltantes(estado)
                print("\n  Instalación terminada.")
            else:
                print("\n  La instalación no terminó bien; sigo con la estructura.")
        else:
            print("  No se instaló nada. Podés hacerlo después con instalar_todo.py.")

    _paso(2, total, "Preparando carpetas y datos")
    resultado = preparar(espacio, con_plantillas=False)
    print(
        f"  Carpetas: {len(resultado['carpetas'])} creada(s)"
        if resultado["carpetas"]
        else "  Carpetas: todas ya existían"
    )
    print(
        f"  Datos: {len(resultado['datos_creados'])} archivo(s) creado(s)"
        if resultado["datos_creados"]
        else "  Datos: todos ya existían"
    )
    if resultado["datos_respetados"]:
        print(f"  Respetados: {len(resultado['datos_respetados'])} archivo(s) tuyo(s), sin tocar")

    _paso(3, total, "Creando plantillas base")
    if args.sin_plantillas:
        print("  --sin-plantillas: no creo plantillas.")
        resultado["plantillas_creadas"] = []
    else:
        creadas, existentes, errores = crear_plantillas(espacio)
        resultado["plantillas_creadas"] = creadas
        resultado["plantillas_error"] = errores
        print(
            f"  Creadas: {len(creadas)} (una por tipo)"
            if creadas
            else "  No hacía falta: cada tipo ya tiene su plantilla"
        )
        if existentes:
            print(f"  Respetados: {len(existentes)} tipo(s) que ya tenían plantilla")
        for tipo, mensaje in errores:
            print(f"  No se pudo crear '{tipo}': {mensaje}")

    _paso(4, total, "Resultado")
    pendientes = datos_pendientes(espacio)
    if pendientes:
        print(
            f"  Datos por completar: {len(pendientes)} archivo(s) con PENDIENTE "
            f"en {ws.mostrar(espacio / 'datos', espacio)}/"
        )
        print("  Eso lo completás vos: el agente no inventa datos.")
    if estado is None:
        print("  Entorno: no se pudo verificar; corré verificar_entorno.py a mano.")
    elif obligatorios:
        print(f"  Entorno: faltan {len(obligatorios)} ({', '.join(obligatorios)}).")
    else:
        print("  Entorno: completo.")
    print(f"  Estructura: lista en {ws.mostrar(espacio)}.")

    print("\nCómo seguir:")
    if pendientes:
        print("  1. Completá los PENDIENTE de tus datos (son tuyos, no los toco).")
    else:
        print("  1. Tus datos ya no tienen PENDIENTE.")
    print("  2. Abrí el menú y elegí una opción:")
    print("       python herramientas/scripts/menu.py")

    if estado is not None and not obligatorios and not resultado["plantillas_error"]:
        print("\nTODO LISTO: la estructura y el entorno quedaron preparados.")

    todo_ok = estado is not None and not obligatorios and not resultado["plantillas_error"]
    return 0 if todo_ok else 1


def selftest() -> int:
    """Prueba de humo en un temporal; no instala ni toca el repositorio."""
    fallos = 0
    import tempfile

    with tempfile.TemporaryDirectory() as temporal:
        base = Path(temporal)
        espacio = base / "espacio"

        resultado = preparar(espacio)
        if len(resultado["carpetas"]) != len(ws.SUBCARPETAS):
            print(f"FALLO preparar() -> carpetas: {len(resultado['carpetas'])}")
            fallos += 1
        if not resultado["datos_creados"]:
            print("FALLO preparar() -> no copió ningún dato")
            fallos += 1
        if len(resultado["plantillas_creadas"]) != len(pl.TIPOS):
            print(f"FALLO preparar() -> plantillas: {len(resultado['plantillas_creadas'])}")
            fallos += 1

        if not resultado["plantillas_creadas"]:
            print("FALLO preparar() -> no creó ninguna plantilla")
            fallos += 1

        pendientes_antes = datos_pendientes(espacio)
        if not pendientes_antes:
            print("FALLO datos_pendientes() -> los contratos traen PENDIENTE")
            fallos += 1

        entidad = espacio / "datos" / "organizacion" / "entidad.csv"
        if not entidad.is_file():
            print("FALLO preparar() -> falta entidad.csv")
            fallos += 1
        else:
            entidad.write_text("MI DATO REAL", encoding="utf-8")

        for tipo in ("informe", "reporte"):
            plantilla = pl.carpeta_destino(espacio) / pl.nombre(
                tipo, "base", pl.extensiones_de(tipo)[0]
            )
            if not plantilla.is_file():
                print(f"FALLO preparar() -> falta la plantilla {plantilla.name}")
                fallos += 1

        segunda = preparar(espacio)
        if segunda["carpetas"] or segunda["datos_creados"] or segunda["plantillas_creadas"]:
            print("FALLO preparar() -> la segunda pasada volvió a crear cosas")
            fallos += 1
        if entidad.read_text(encoding="utf-8") != "MI DATO REAL":
            print("FALLO preparar() -> pisó un dato del usuario")
            fallos += 1
        if datos_pendientes(espacio):
            print("FALLO datos_pendientes() -> sigue marcando un archivo ya completo")
            fallos += 1

        # El plan no debe escribir nada.
        vacio = base / "vacio"
        with redirect_stdout(io.StringIO()):
            mostrar_plan(vacio, {"faltantes_obligatorios": [], "faltantes_opcionales": []})
        if vacio.exists():
            print("FALLO mostrar_plan() -> escribió en disco")
            fallos += 1

    if fallos:
        print(f"\nselftest de empezar: {fallos} fallo(s)")
        return 1
    print("selftest de empezar: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
