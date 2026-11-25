#!/usr/bin/env python3
"""Utilidades de entorno compartidas por los scripts de ``herramientas/scripts/``.

Sólo biblioteca estándar. Hoy expone una sola cosa, y es la que evita el error
clásico de Windows: un programa recién instalado con ``winget`` no aparece en el
``PATH`` de la ventana que ya estaba abierta.

Windows guarda el ``PATH`` en el registro, y cada proceso hereda una copia al
arrancar. Por eso ``winget install Pandoc`` deja el ``PATH`` correcto en el
registro pero invisible para el proceso que lo instaló y para cualquier otro que
ya estuviera corriendo. La solución no es pedirle al usuario «cerrá y reabrí la
terminal» —un usuario no técnico no hace eso— sino releer el registro.
"""

from __future__ import annotations

import os
import sys


def refrescar_path() -> None:
    """Relee el ``PATH`` del registro de Windows y lo suma al del proceso.

    En sistemas que no son Windows no hace nada: ahí el ``PATH`` se resuelve por
    otro mecanismo y no existe este problema.

    No escribe en el registro: sólo lee. El cambio es únicamente para el proceso
    actual.
    """
    if sys.platform != "win32":
        return
    try:
        import winreg
    except ImportError:  # pragma: no cover - Windows siempre trae winreg
        return

    claves = (
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ),
        (winreg.HKEY_CURRENT_USER, "Environment"),
    )

    del_registro: list[str] = []
    for raiz, subclave in claves:
        try:
            with winreg.OpenKey(raiz, subclave) as clave:
                valor, _ = winreg.QueryValueEx(clave, "Path")
        except OSError:
            continue
        del_registro.append(os.path.expandvars(str(valor)))

    actual = os.environ.get("PATH", "")
    vistos: set[str] = set()
    final: list[str] = []
    for bloque in (actual, *del_registro):
        for entrada in bloque.split(os.pathsep):
            limpio = entrada.strip()
            if limpio and limpio.lower() not in vistos:
                vistos.add(limpio.lower())
                final.append(limpio)
    os.environ["PATH"] = os.pathsep.join(final)
