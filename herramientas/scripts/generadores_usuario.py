#!/usr/bin/env python3
"""Contrato de los generadores propios del usuario.

El usuario puede escribir su propia plantilla como código (Python o JavaScript)
y producir **todos** sus documentos con ella. Ese código es de su propiedad:
vive en ``usuario/generadores/``, no se versiona, no lo modifica el agente y el
motor nunca lo importa.

Acá vive únicamente el CONTRATO:

* descubrimiento por manifiesto ``generador.json``;
* payload JSON con el contenido ya resuelto **y** los datos crudos;
* invocación como subproceso, para que un error del generador del usuario no
  rompa el motor genérico.

Detalle completo en ``herramientas/docs/contrato-generador.md``.

Uso::

    python herramientas/scripts/listar_generadores.py
    python herramientas/scripts/generar_documento.py --tipo informe
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
DIR_GENERADORES = RAIZ / "usuario" / "generadores"
NOMBRE_MANIFIESTO = "generador.json"
VERSION_PAYLOAD = 1
TIEMPO_LIMITE = 180


@dataclass(frozen=True)
class Generador:
    """Un generador propio del usuario, tal como lo declara su manifiesto."""

    nombre: str
    carpeta: Path
    tipos: tuple[str, ...]
    script: Path
    comando: tuple[str, ...]
    descripcion: str = ""

    def cubre(self, tipo: str) -> bool:
        return tipo.strip().lower() in self.tipos

    def cubre_todo(self) -> bool:
        """El generador declara ``"*"``: aplica a cualquier tipo de documento."""
        return "*" in self.tipos


def _plano(tabla: dict[str, Any] | None) -> dict[str, str]:
    """Convierte una tabla de clave/valor en un mapa campo -> valor."""
    if not tabla:
        return {}
    cabecera, filas = tabla.get("cabecera", []), tabla.get("filas", [])
    if not filas:
        return {}
    if cabecera[:2] == ["clave", "valor"]:
        return {fila[0].strip(): fila[1].strip() for fila in filas if len(fila) >= 2}
    return {clave: valor.strip() for clave, valor in zip(cabecera, filas[0])}


def _leer_manifiesto(carpeta: Path) -> dict[str, Any]:
    ruta = carpeta / NOMBRE_MANIFIESTO
    try:
        with ruta.open("r", encoding="utf-8-sig") as archivo:
            manifiesto = json.load(archivo)
    except json.JSONDecodeError as error:
        raise ValueError(f"{ruta}: manifiesto inválido ({error})") from None
    if not isinstance(manifiesto, dict):
        raise ValueError(f"{ruta}: el manifiesto debe ser un objeto JSON")
    return manifiesto


def cargar(carpeta: Path) -> Generador:
    """Carga un generador desde la carpeta que lo contiene."""
    carpeta = Path(carpeta).resolve()
    if not carpeta.is_dir():
        raise ValueError(f"no existe la carpeta del generador: {carpeta}")

    manifiesto = _leer_manifiesto(carpeta)

    tipos = manifiesto.get("tipos")
    if not isinstance(tipos, list) or not tipos or not all(isinstance(t, str) for t in tipos):
        raise ValueError(
            f"{carpeta / NOMBRE_MANIFIESTO}: falta 'tipos' o no es una lista de texto. "
            "Ejemplo: {\"nombre\": \"mi-plantilla\", \"tipos\": [\"informe\"]}"
        )
    tipos = tuple(t.strip().lower() for t in tipos if t.strip())
    if not tipos:
        raise ValueError(f"{carpeta / NOMBRE_MANIFIESTO}: 'tipos' está vacío")

    script = manifiesto.get("script")
    if script is None:
        for candidato in ("generador.py", "generador.js"):
            if (carpeta / candidato).is_file():
                script = candidato
                break
        else:
            raise ValueError(
                f"{carpeta}: no hay generador.py ni generador.js. "
                "Indicá el archivo con \"script\" en el manifiesto."
            )
    script = Path(script)
    if script.is_absolute() or ".." in script.parts:
        raise ValueError(f"{carpeta / NOMBRE_MANIFIESTO}: 'script' debe ser relativo a la carpeta")
    ruta_script = (carpeta / script).resolve()
    if not ruta_script.is_file():
        raise ValueError(f"{carpeta}: el script '{script}' no existe")
    if not ruta_script.is_relative_to(carpeta):
        raise ValueError(f"{carpeta}: el script '{script}' sale de la carpeta del generador")

    comando = manifiesto.get("comando")
    if comando is None:
        comando = ["python"] if script.suffix == ".py" else ["node"]
    if not isinstance(comando, list) or not comando or not all(isinstance(c, str) for c in comando):
        raise ValueError(f"{carpeta / NOMBRE_MANIFIESTO}: 'comando' debe ser una lista de texto")

    return Generador(
        nombre=str(manifiesto.get("nombre") or carpeta.name),
        carpeta=carpeta,
        tipos=tipos,
        script=ruta_script,
        comando=tuple(comando),
        descripcion=str(manifiesto.get("descripcion") or ""),
    )


def descubrir(directorio: Path | None = None) -> list[Generador]:
    """Devuelve los generadores del usuario, ordenados por nombre."""
    base = Path(directorio) if directorio else DIR_GENERADORES
    if not base.is_dir():
        return []
    generadores: list[Generador] = []
    for carpeta in sorted(p for p in base.iterdir() if p.is_dir()):
        if not (carpeta / NOMBRE_MANIFIESTO).is_file():
            continue
        generadores.append(cargar(carpeta))
    return sorted(generadores, key=lambda g: g.nombre)


def seleccionar(generadores: list[Generador], tipo: str) -> Generador | None:
    """Devuelve el generador que declara ese tipo.

    Un generador con ``"tipos": ["*"]`` sirve para todos los documentos: se usa
    sólo si no hay otro que declare el tipo explícitamente. Si más de uno
    qualifies, falla: la ambigüedad se reporta, no se resuelve en silencio.
    """
    clave = tipo.strip().lower()
    candidatos = [g for g in generadores if g.cubre(clave)]
    if not candidatos:
        candidatos = [g for g in generadores if g.cubre_todo()]
    if not candidatos:
        return None
    if len(candidatos) > 1:
        nombres = ", ".join(f"'{g.nombre}'" for g in candidatos)
        raise ValueError(
            f"hay {len(candidatos)} generadores del usuario para el tipo '{clave}': {nombres}. "
            "Dejá uno solo con ese tipo o ajustá 'tipos' en su manifiesto."
        )
    return candidatos[0]


def construir_payload(
    spec: dict[str, Any],
    datos: dict[str, dict[str, Any]],
    bloques: list[dict[str, Any]],
    indice: list[dict[str, Any]],
    salida: str,
    constantes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Arma el JSON que consume el generador del usuario.

    El contenido (``bloques``) ya viene resuelto y validado por el motor: no
    hay placeholders sin resolver ni ``PENDIENTE`` en lo que el documento usa.
    Los ``datos`` crudos van aparte, para que el generador pueda aplicar su
    propia plantilla a los campos que el motor no usó.
    """
    if Path(salida).is_absolute():
        raise ValueError("'salida' debe ser una ruta relativa a la raíz del repositorio")
    titulo = spec.get("titulo", spec["tipo"])
    return {
        "version": VERSION_PAYLOAD,
        "tipo": spec["tipo"],
        "titulo": titulo,
        "formato": spec["formato"],
        "pie": f"{titulo} · v1.0",
        "salida": salida,
        "bloques": bloques,
        "indice": indice,
        "entidad": _plano(datos.get("entidad")),
        "datos": datos,
        "constantes": constantes or {},
    }


def ejecutar(
    generador: Generador,
    payload: dict[str, Any],
    raiz: Path | None = None,
    timeout: int = TIEMPO_LIMITE,
) -> Path:
    """Ejecuta el generador del usuario como subproceso y devuelve la salida."""
    base = Path(raiz).resolve() if raiz else RAIZ

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".json", delete=False
    ) as temporal:
        json.dump(payload, temporal, ensure_ascii=False)
        ruta_payload = Path(temporal.name)

    entorno = os.environ.copy()
    nodos = base / "node_modules"
    if nodos.is_dir():
        entorno["NODE_PATH"] = str(nodos) + (
            os.pathsep + entorno["NODE_PATH"] if entorno.get("NODE_PATH") else ""
        )

    comando = [*generador.comando, str(generador.script), "--entrada", str(ruta_payload)]
    try:
        resultado = subprocess.run(
            comando,
            cwd=base,
            env=entorno,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=timeout,
        )
    finally:
        ruta_payload.unlink(missing_ok=True)

    if resultado.returncode != 0:
        detalle = (resultado.stderr or resultado.stdout or "").strip()
        raise ValueError(
            f"el generador '{generador.nombre}' terminó con código {resultado.returncode}"
            + (f": {detalle}" if detalle else "")
        )

    salida = base / payload["salida"]
    if not salida.is_file() or salida.stat().st_size == 0:
        raise ValueError(
            f"el generador '{generador.nombre}' no produjo un archivo válido en {payload['salida']}"
        )
    return salida
