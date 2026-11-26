#!/usr/bin/env python3
"""Módulo compartido de plantillas del usuario.

No es un script: lo usan ``instalar_plantilla.py`` y ``nueva_plantilla.py``
para que las reglas vivan en un solo lugar:

* qué tipos de documento existen (el catálogo de ``tipos-de-documento.md``);
* qué extensiones de plantilla acepta cada tipo;
* cómo se llama una plantilla: ``<tipo>-<variante>.<ext>``;
* dónde vive: ``plantillas/propias/`` (por defecto) o ``plantillas/oficiales/``.

El contrato de escritura es el de ``init_local.py``: la plantilla destino
**no existe** y se crea; si ya existe, se rechaza con mensaje explícito. Nunca
se sobrescribe y nunca se mueve ni borra el original.

Sólo biblioteca estándar.
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace as ws  # noqa: E402

PATRON_NO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")

# tipo -> extensiones de plantilla válidas, en orden de precedencia del catálogo.
TIPOS: dict[str, tuple[str, ...]] = {
    "memorandum": ("docx", "md"),
    "circular": ("docx", "md"),
    "informe": ("docx", "md"),
    "manual": ("docx", "md"),
    "plan-operativo": ("docx", "md"),
    "oficio": ("docx", "md"),
    "solicitud": ("docx", "md"),
    "constancia": ("docx", "md"),
    "acta": ("docx", "md"),
    "comunicado": ("docx", "md"),
    "cotizacion": ("xlsx", "docx"),
    "reporte": ("xlsx",),
}


def slug(texto: str) -> str:
    """Convierte un texto libre en un slug seguro para nombres de archivo."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return PATRON_NO_ALFANUMERICO.sub("-", sin_tildes.lower()).strip("-")


def extensiones_de(tipo: str) -> tuple[str, ...]:
    if tipo not in TIPOS:
        raise ValueError(
            f"tipo '{tipo}' desconocido. Válidos: {', '.join(sorted(TIPOS))}"
        )
    return TIPOS[tipo]


def validar(tipo: str, extension: str) -> str:
    """Valida el par tipo/extensión y devuelve la extensión normalizada."""
    extensiones = extensiones_de(tipo)
    extension = extension.lower().lstrip(".")
    if extension not in extensiones:
        raise ValueError(
            f"una plantilla de '{tipo}' no puede ser '.{extension}'. "
            f"Válidas para ese tipo: {', '.join('.' + e for e in extensiones)}"
        )
    return extension


def nombre(tipo: str, variante: str, extension: str) -> str:
    """Nombre canónico de una plantilla: ``<tipo>-<variante>.<ext>``."""
    cuerpo = slug(variante)
    if not cuerpo:
        raise ValueError("la variante no produce un slug válido; usá letras o números")
    return f"{tipo}-{cuerpo}.{extension}"


def carpeta_destino(espacio: Path, oficiales: bool = False) -> Path:
    """Carpeta de plantillas del espacio de trabajo (propias por defecto)."""
    subcarpeta = "oficiales" if oficiales else "propias"
    return Path(espacio) / "plantillas" / subcarpeta


def instalar(
    origen: Path,
    espacio: Path,
    tipo: str,
    variante: str,
    oficiales: bool = False,
) -> Path:
    """Copia la plantilla del usuario a la carpeta que le corresponde.

    El original no se toca: se copia. El destino no puede existir; si existe,
    se rechaza con mensaje explícito — dos plantillas del mismo tipo rompen la
    precedencia, así que no hay ``-v2`` silencioso.
    """
    origen = Path(origen)
    if not origen.is_file():
        raise ValueError(f"no existe el archivo de origen: {origen}")

    extension = validar(tipo, origen.suffix)
    destino = carpeta_destino(espacio, oficiales) / nombre(tipo, variante, extension)
    if destino.exists():
        raise ValueError(
            f"ya existe la plantilla {destino.name} en {destino.parent}. "
            "Nunca se sobrescribe: usá otra --variante o borrá la existente vos mismo."
        )
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origen, destino)
    return destino


def selftest() -> int:
    """Prueba de humo del módulo, en un temporal. No toca el repositorio."""
    fallos = 0

    casos_slug = [
        ("Corporativa", "corporativa"),
        ("MEMBRETE 2026", "membrete-2026"),
        ("Con tildes: organización", "con-tildes-organizacion"),
    ]
    for entrada, esperado in casos_slug:
        obtenido = slug(entrada)
        if obtenido != esperado:
            print(f"FALLO slug({entrada!r}) -> {obtenido!r}; esperado {esperado!r}")
            fallos += 1

    if nombre("informe", "Base", "docx") != "informe-base.docx":
        print("FALLO nombre() -> no respeta <tipo>-<variante>.<ext>")
        fallos += 1

    try:
        validar("reporte", "docx")
    except ValueError:
        pass
    else:
        print("FALLO validar('reporte', 'docx') -> no se rechazó")
        fallos += 1

    try:
        extensiones_de("inventado")
    except ValueError:
        pass
    else:
        print("FALLO extensiones_de('inventado') -> no se rechazó")
        fallos += 1

    with tempfile.TemporaryDirectory() as temporal:
        base = Path(temporal)
        origen = base / "mia.docx"
        origen.write_bytes(b"contenido de prueba")

        destino = instalar(origen, base, "oficio", "Corporativa")
        if destino != base / "plantillas" / "propias" / "oficio-corporativa.docx":
            print(f"FALLO instalar() -> destino inesperado: {destino}")
            fallos += 1
        if destino.read_bytes() != origen.read_bytes():
            print("FALLO instalar() -> el contenido copiado no coincide")
            fallos += 1
        if origen.exists() is not True:
            print("FALLO instalar() -> el original debe quedar donde está")
            fallos += 1

        try:
            instalar(origen, base, "oficio", "Corporativa")
        except ValueError as error:
            if "ya existe" not in str(error):
                print(f"FALLO instalar() -> colisión con mensaje inesperado: {error}")
                fallos += 1
        else:
            print("FALLO instalar() -> la colisión no se rechazó")
            fallos += 1

        destino_oficial = instalar(origen, base, "oficio", "Corporativa", oficiales=True)
        if destino_oficial.parent.name != "oficiales":
            print(f"FALLO instalar(oficiales=True) -> carpeta inesperada: {destino_oficial}")
            fallos += 1

    if fallos:
        print(f"\nselftest de plantillas: {fallos} fallo(s)")
        return 1
    print("selftest de plantillas: OK")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())
