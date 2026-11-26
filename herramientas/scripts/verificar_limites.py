#!/usr/bin/env python3
"""Verifica que la frontera entre la zona del usuario y las herramientas se respete.

La regla que controla es una sola:

    Nada de ``usuario/`` se versiona, salvo los ``.gitkeep`` de estructura.

Controles:

1. Ningún archivo de ``usuario/`` aparece en ``git ls-files`` (salvo ``.gitkeep``).
2. Ningún contrato ``*.example`` quedó dentro de ``usuario/``.
3. La estructura esperada de la zona del usuario existe.
4. Existen contratos en ``herramientas/contratos/``.
5. Inventario informativo de lo que hay en la zona del usuario.

Sólo lee: no crea, no corrige y no borra nada.

Sólo usa la biblioteca estándar.

Uso:
    python herramientas/scripts/verificar_limites.py
    python herramientas/scripts/verificar_limites.py --workspace D:\\clientes\\clinica-a

Con ``--workspace`` apuntando a una carpeta fuera del repositorio, el control de
git informa que esa zona no puede versionarse y sigue con el resto.

Salida: ``0`` si la frontera se respeta, ``1`` si algo se rompió.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace as ws  # noqa: E402

RAIZ = ws.RAIZ
DIR_CONTRATOS = RAIZ / "herramientas" / "contratos"

# Relativas al espacio de trabajo (la carpeta que contiene datos/, entregables/, ...).
ESTRUCTURA_ESPERADA = ws.SUBCARPETAS


def archivos_versionados() -> list[str] | None:
    """Devuelve las rutas versionadas bajo usuario/, o None si git no responde."""
    try:
        resultado = subprocess.run(
            ["git", "ls-files", "--", "usuario"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if resultado.returncode != 0:
        return None
    return [linea.strip() for linea in resultado.stdout.splitlines() if linea.strip()]


def contar_archivos(directorio: Path) -> int:
    if not directorio.exists():
        return 0
    return sum(1 for ruta in directorio.rglob("*") if ruta.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ws.agregar_argumento(parser)
    args = parser.parse_args(argv)
    espacio = ws.resolver(args.workspace)
    zona_del_repo = espacio == (RAIZ / "usuario").resolve()
    sufijo_ws = "" if zona_del_repo else f" --workspace {espacio}"

    errores: list[str] = []
    advertencias: list[str] = []

    print(f"Repositorio: {RAIZ}")
    print(f"Espacio de trabajo: {ws.mostrar(espacio)}")
    print("Frontera: zona del usuario (fuera de git) | herramientas/ (nuestra)\n")

    # 1. Nada versionado en la zona del usuario, salvo .gitkeep
    if not zona_del_repo:
        print("  [OK]    espacio de trabajo externo al repositorio: no puede versionarse")
    else:
        versionados = archivos_versionados()
        if versionados is None:
            advertencia = "no se pudo consultar git; el control de versionado se omitió"
            advertencias.append(advertencia)
            print(f"  [AVISO] {advertencia}")
        else:
            intrusos = [ruta for ruta in versionados if not ruta.endswith(".gitkeep")]
            if intrusos:
                for ruta in intrusos:
                    errores.append(f"{ruta}: archivo del usuario versionado en git")
            else:
                print(
                    f"  [OK]    ningún archivo del usuario versionado "
                    f"({len(versionados)} .gitkeep)"
                )

    # 2. Contratos fuera de la zona del usuario
    if espacio.exists():
        filtrados = sorted(espacio.rglob("*.example"))
        for ruta in filtrados:
            errores.append(
                f"{ws.mostrar(ruta, espacio)}: contrato *.example dentro de la zona del usuario"
            )
        if not filtrados:
            print("  [OK]    ningún contrato *.example en la zona del usuario")

    # 3. Estructura esperada
    faltantes = [relativa for relativa in ESTRUCTURA_ESPERADA if not (espacio / relativa).is_dir()]
    if faltantes:
        for relativa in faltantes:
            advertencias.append(
                f"{relativa}/: carpeta ausente — ejecutá: "
                f"python herramientas/scripts/init_local.py{sufijo_ws}"
            )
    else:
        print(f"  [OK]    estructura del usuario completa ({len(ESTRUCTURA_ESPERADA)} carpetas)")

    # 4. Contratos disponibles
    contratos = sorted(DIR_CONTRATOS.glob("**/*.example")) if DIR_CONTRATOS.exists() else []
    if not contratos:
        errores.append("herramientas/contratos/: no hay ningún contrato *.example")
    else:
        print(f"  [OK]    contratos disponibles: {len(contratos)}")

    # 5. Inventario informativo
    print("\nInventario de la zona del usuario:")
    if espacio.exists():
        for carpeta in ("datos", "plantillas", "generadores", "recursos", "entregables"):
            ruta = espacio / carpeta
            total = contar_archivos(ruta)
            print(f"  {carpeta:<12} {total} archivo(s)")
    else:
        advertencias.append(f"{ws.mostrar(espacio)}: la zona no existe todavía")

    if errores:
        print(f"\nErrores ({len(errores)}):")
        for mensaje in errores:
            print(f"  [ERROR] {mensaje}")
    if advertencias:
        print(f"\nAdvertencias ({len(advertencias)}):")
        for mensaje in advertencias:
            print(f"  [AVISO] {mensaje}")

    if errores:
        print("\nResultado: FRONTERA VIOLADA — revisá antes de commitear.")
        return 1

    print("\nResultado: la frontera entre usuario/ y herramientas/ se respeta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
