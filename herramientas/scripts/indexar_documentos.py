#!/usr/bin/env python3
"""Mapea una carpeta completa y guarda un índice de sus documentos.

El usuario destino vive en una selva de carpetas —`FOLDER-PRINCIPAL` con
subcarpetas, el repositorio adentro de una de ellas— y trabaja con Word y
PDF, muchos escaneados. Recorrer esa selva a pie, cada vez, no escala: este
comando la mapea **una vez** y guarda el mapa en ``<espacio>/indice/`` para
que ``buscar_documentos.py`` lo consulte en milisegundos.

Qué registra de cada documento (los formatos de ``leer_documento.py``):
extensión, carpeta, tamaño, fecha, páginas/párrafos/tablas/hojas, título y
autor, el texto completo (buscable, salvo ``--sin-texto``) y ``escaneado``
para los PDF sin texto extraíble. Lo que no se puede leer no se omite: queda
en el mapa con su error. Con ``--todo``, los archivos que no son documentos
entran como entradas de sólo nombre.

El índice es **incremental**: re-indexar la misma raíz sólo relee lo nuevo o
lo cambiado (compara tamaño y fecha); el resto se conserva tal cual, texto
incluido. Los originales jamás se tocan: el mapeo sólo lee.

Uso::

    python herramientas/scripts/indexar_documentos.py --ruta D:\\FOLDER-PRINCIPAL
    python herramientas/scripts/indexar_documentos.py --ruta D:\\FOLDER-PRINCIPAL --sin-texto
    python herramientas/scripts/indexar_documentos.py --ruta "D:\\FOLDER 1\\contrato.docx"
    python herramientas/scripts/indexar_documentos.py --ruta D:\\FOLDER-PRINCIPAL --con-ocr

Con ``--con-ocr`` los PDF escaneados y las imágenes sin texto se reintentan
con Tesseract y el texto reconocido queda en ``texto_ocr``: la búsqueda lo
encuentra igual que el texto normal. Necesita la cadena OCR
(`ocr_documento.py`: Tesseract + `pytesseract`); si falta, el archivo igual
queda en el índice, con su `ocr_error`.

El índice vive en el espacio del usuario (``indice/``, creado por
``init_local.py``), un JSON por raíz: ``<slug>-<hash6>.json``. Nunca se
versiona: puede contener texto de documentos privados.

Códigos de salida: ``0`` mapeada (aunque haya errores de lectura, que van en
el resumen), ``1`` la ruta no existe o el índice no se pudo escribir.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leer_documento as lector  # noqa: E402
import ocr_documento as mod_ocr  # noqa: E402
import plantillas as pl  # noqa: E402
import workspace as ws  # noqa: E402

OCR_EXTS = (".pdf", *mod_ocr.EXTENSIONES_IMAGEN)

# Carpetas que no aportan documentos y sí ruido (o candidatas a ciclos).
CARPETAS_EXCLUIDAS = {
    "$recycle.bin",
    "system volume information",
    ".git",
    ".codegraph",
    ".atl",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
}


def slug(texto: str) -> str:
    """Slug liviano para nombrar el archivo de índice."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-") or "raiz"


def ruta_indice(espacio: Path, raiz: Path) -> Path:
    """Archivo de índice de una raíz: ``<slug>-<hash6>.json``.

    El hash evita que dos raíces con el mismo nombre compartan archivo.
    """
    huella = hashlib.md5(str(raiz).lower().encode("utf-8")).hexdigest()[:6]
    return Path(espacio) / "indice" / f"{slug(raiz.name)}-{huella}.json"


def cargar(ruta: Path) -> dict | None:
    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, json.JSONDecodeError):
        return None


def _resumen_de_lectura(resultado: dict) -> dict:
    """Metadatos compactos que valen la pena en un índice."""
    resumen = dict(resultado.get("metadatos", {}))
    if "paginas" in resultado:
        resumen["paginas"] = str(len(resultado["paginas"]))
    if "parrafos" in resultado:
        resumen["parrafos"] = str(len(resultado["parrafos"]))
        resumen["tablas"] = str(len(resultado["tablas"]))
    if "hojas" in resultado:
        resumen["hojas"] = ", ".join(hoja["nombre"] for hoja in resultado["hojas"][:5])
    return resumen


def _entrada_documento(ruta: Path, raiz: Path, con_texto: bool, sello: tuple) -> dict:
    """Lee un documento y arma su entrada. Falla amable: deja el error.

    Tamaño y fecha salen del ``stat`` del walk (``sello``), no de la lectura:
    así un archivo que no se pudo leer conserva su sello y el incremental no
    lo re-procesa en cada corrida.
    """
    entrada: dict = {
        "ruta": ruta.relative_to(raiz).as_posix(),
        "nombre": ruta.name,
        "carpeta": ruta.parent.relative_to(raiz).as_posix(),
        "extension": ruta.suffix.lower(),
        "documento": True,
        "bytes": sello[0],
        "mtime": sello[1],
    }
    try:
        resultado = lector.leer(ruta)
        entrada.update(
            {
                "escaneado": "aviso" in resultado,
                "metadatos": _resumen_de_lectura(resultado),
                "texto": resultado["texto"] if con_texto else None,
                "error": None,
            }
        )
    except Exception as error:  # un archivo roto no puede romper el mapa
        entrada.update({"escaneado": None, "metadatos": {}, "texto": None, "error": str(error)})
    return entrada


def _entrada_simple(ruta: Path, raiz: Path, sello: tuple) -> dict:
    """Entrada de sólo nombre para archivos que no son documentos."""
    return {
        "ruta": ruta.relative_to(raiz).as_posix(),
        "nombre": ruta.name,
        "carpeta": ruta.parent.relative_to(raiz).as_posix(),
        "extension": ruta.suffix.lower(),
        "documento": False,
        "bytes": sello[0],
        "mtime": sello[1],
        "escaneado": None,
        "metadatos": {},
        "texto": None,
        "error": None,
    }


def _sello(entrada: dict) -> tuple | None:
    """Marca de frescura de una entrada (tamaño + fecha de modificación)."""
    if entrada.get("bytes") is None or entrada.get("mtime") is None:
        return None
    return (entrada.get("bytes"), entrada.get("mtime"))


def _aplicar_ocr(entrada: dict, ruta: Path, idioma: str, dpi: int) -> dict:
    """Reintenta con OCR una entrada sin texto (escaneado o imagen vacía).

    Guarda `texto_ocr` y `ocr` (True si hubo texto). Si el OCR falla, guarda
    `ocr_error` y deja `texto_ocr` en None: el mapa no se rompe por un OCR
    que no corre. Nunca modifica el original: sólo lee.
    """
    try:
        resultado = mod_ocr.ocr(ruta, idioma=idioma, dpi=dpi)
    except Exception as error:
        entrada["texto_ocr"] = None
        entrada["ocr"] = False
        entrada["ocr_error"] = str(error)
        return entrada
    texto = (resultado.get("texto") or "").strip()
    entrada["texto_ocr"] = texto or None
    entrada["ocr"] = bool(texto)
    entrada["ocr_error"] = None
    if texto:
        metadatos = entrada.get("metadatos") or {}
        metadatos["ocr"] = "tesseract"
        entrada["metadatos"] = metadatos
    return entrada


def indexar(
    raiz: Path,
    espacio: Path,
    con_texto: bool = True,
    todo: bool = False,
    con_ocr: bool = False,
    idioma_ocr: str = "spa",
    dpi_ocr: int = 300,
) -> dict:
    """Mapea ``raiz`` completa y devuelve el resumen de lo que hizo."""
    raiz = Path(raiz).resolve()
    if not raiz.is_dir():
        raise ValueError(f"no existe la carpeta a mapear: {raiz}")

    destino = ruta_indice(espacio, raiz)
    anterior = cargar(destino)
    previos: dict[str, dict] = {}
    if (
        anterior
        and anterior.get("con_texto") == con_texto
        and anterior.get("con_ocr", False) == con_ocr
    ):
        previos = {entrada["ruta"]: entrada for entrada in anterior.get("archivos", [])}

    encontrados: dict[str, tuple] = {}
    # os.walk y no Path.walk: la segunda existe recién desde Python 3.12 y el
    # repositorio funciona desde 3.10.
    for carpeta_str, carpetas, archivos in os.walk(raiz):
        carpeta_actual = Path(carpeta_str)
        # Adentro del walk: filtrar ruido sin distinguir mayúsculas.
        carpetas[:] = [
            nombre for nombre in carpetas if nombre.lower() not in CARPETAS_EXCLUIDAS and not nombre.startswith(".")
        ]
        for nombre in archivos:
            if nombre.startswith("~$"):
                continue
            ruta = carpeta_actual / nombre
            try:
                estado = ruta.stat()
            except OSError:
                continue
            encontrados[ruta.relative_to(raiz).as_posix()] = (estado.st_size, int(estado.st_mtime))

    entradas: list[dict] = []
    nuevos = cambiados = reutilizados = errores = 0
    for relativa, sello in encontrados.items():
        previa = previos.get(relativa)
        if previa is not None and _sello(previa) == sello:
            entradas.append(previa)
            reutilizados += 1
        else:
            ruta = raiz / relativa
            if ruta.suffix.lower() in lector.LECTORES:
                entrada = _entrada_documento(ruta, raiz, con_texto, sello)
            elif todo:
                entrada = _entrada_simple(ruta, raiz, sello)
            else:
                continue
            if con_ocr and entrada.get("documento"):
                extension = ruta.suffix.lower()
                sin_texto = not (entrada.get("texto") or "").strip()
                if extension in OCR_EXTS and (entrada.get("escaneado") or sin_texto):
                    entrada = _aplicar_ocr(entrada, ruta, idioma_ocr, dpi_ocr)
            if previa is not None:
                cambiados += 1
            else:
                nuevos += 1
            entradas.append(entrada)

    errores = sum(1 for entrada in entradas if entrada.get("error"))
    escaneados = sum(1 for entrada in entradas if entrada.get("escaneado"))
    con_ocr_ok = sum(1 for entrada in entradas if entrada.get("texto_ocr"))
    ocr_errores = sum(1 for entrada in entradas if entrada.get("ocr_error"))
    convertidos = sum(
        1 for entrada in entradas if (entrada.get("metadatos") or {}).get("convertido_con")
    )

    entradas.sort(key=lambda entrada: entrada["ruta"])
    indice = {
        "raiz": str(raiz),
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "con_texto": con_texto,
        "con_ocr": con_ocr,
        "idioma_ocr": idioma_ocr if con_ocr else None,
        "documentos": sum(1 for entrada in entradas if entrada["documento"]),
        "archivos": entradas,
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")

    return {
        "raiz": str(raiz),
        "indice": str(destino),
        "total": len(entradas),
        "nuevos": nuevos,
        "cambiados": cambiados,
        "reutilizados": reutilizados,
        "errores": errores,
        "escaneados": escaneados,
        "con_ocr": con_ocr_ok,
        "ocr_errores": ocr_errores,
        "convertidos": convertidos,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ruta", help="carpeta (o archivo) a mapear")
    parser.add_argument(
        "--sin-texto",
        action="store_true",
        help="índice liviano: nombres y metadatos, sin el texto de los documentos",
    )
    parser.add_argument("--todo", action="store_true", help="incluye archivos que no son documentos (sólo nombre)")
    parser.add_argument(
        "--con-ocr",
        action="store_true",
        help="reintenta con OCR los PDF escaneados e imágenes sin texto (necesita Tesseract)",
    )
    parser.add_argument("--idioma-ocr", default="spa", help="idiomas Tesseract para --con-ocr (por defecto: spa)")
    parser.add_argument("--dpi-ocr", type=int, default=300, help="resolución del render para --con-ocr (por defecto: 300)")
    parser.add_argument("--json", action="store_true", help="resumen como JSON")
    parser.add_argument("--selftest", action="store_true", help="prueba de humo; no toca nada")
    ws.agregar_argumento(parser)
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.ruta:
        parser.error("hace falta --ruta: la carpeta (o archivo) a mapear")

    espacio = ws.resolver(args.workspace)
    origen = Path(args.ruta).expanduser()
    if origen.is_file():
        origen = origen.parent

    try:
        resumen = indexar(
            origen,
            espacio,
            con_texto=not args.sin_texto,
            todo=args.todo,
            con_ocr=args.con_ocr,
            idioma_ocr=args.idioma_ocr,
            dpi_ocr=args.dpi_ocr,
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
        return 0

    print(f"Espacio de trabajo: {ws.mostrar(espacio)}")
    print(f"Raíz mapeada: {resumen['raiz']}")
    print(f"Índice: {resumen['indice']}")
    print(f"Archivos: {resumen['total']}  (nuevos {resumen['nuevos']}, "
          f"cambiados {resumen['cambiados']}, sin cambios {resumen['reutilizados']})")
    if resumen["escaneados"]:
        print(f"PDF escaneados: {resumen['escaneados']} — sin texto extraíble; se buscan con "
              "buscar_documentos.py --escaneados")
    if resumen.get("convertidos"):
        print(f"Convertidos con LibreOffice: {resumen['convertidos']} — formatos viejos "
              "(.doc/.xls); el original no se tocó")
    if resumen.get("con_ocr"):
        print(f"Con OCR: {resumen['con_ocr']} — su texto también se busca")
    if resumen.get("ocr_errores"):
        print(f"Errores de OCR: {resumen['ocr_errores']} — falta Tesseract o falló la conversión; "
              "el archivo igual quedó en el índice")
    if resumen["errores"]:
        print(f"Errores de lectura: {resumen['errores']} — quedaron en el índice con su error")
    print("Los originales no se tocaron: el mapeo sólo lee.")
    return 0


def selftest() -> int:
    """Prueba de humo del indexador en un temporal; no toca el repositorio."""
    fallos = 0
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as temporal:
        base = Path(temporal)
        raiz = base / "selva"
        (raiz / "FOLDER 1").mkdir(parents=True)
        (raiz / "FOLDER 1").joinpath("nota.txt").write_text("texto de la nota", encoding="utf-8")
        (raiz / "FOLDER 1").joinpath("falso.docx").write_bytes(b"no es un zip")
        (raiz / "FOLDER 2").mkdir()
        (raiz / "FOLDER 2").joinpath("informe.md").write_text("# Título\n\ncuerpo", encoding="utf-8")
        (raiz / ".git").mkdir()
        (raiz / ".git").joinpath("config").write_text("x", encoding="utf-8")
        (raiz / "suelto.exe").write_bytes(b"binario")

        espacio = base / "espacio"
        resumen = indexar(raiz, espacio)

        if resumen["total"] != 3 or resumen["errores"] != 1:
            print(f"FALLO indexar() -> total/errores inesperados: {resumen}")
            fallos += 1

        indice = cargar(Path(resumen["indice"]))
        rutas = {entrada["ruta"]: entrada for entrada in indice["archivos"]}
        if "FOLDER 1/falso.docx" in rutas and not rutas["FOLDER 1/falso.docx"]["error"]:
            print("FALLO: el docx corrupto quedó sin error registrado")
            fallos += 1
        if ".git/config" in rutas:
            print("FALLO: una carpeta excluida entró al índice")
            fallos += 1

        # Re-indexar sin cambios: todo reutilizado, nada re-leído.
        segunda = indexar(raiz, espacio)
        if segunda["nuevos"] or segunda["cambiados"] or segunda["reutilizados"] != 3:
            print(f"FALLO incremental -> {segunda}")
            fallos += 1

        # Cambia un archivo: se relee.
        nota = raiz / "FOLDER 1" / "nota.txt"
        nota.write_text("texto de la nota, ahora más largo", encoding="utf-8")
        os.utime(nota, (2_000_000_000, 2_000_000_000))
        tercera = indexar(raiz, espacio)
        if tercera["cambiados"] != 1 or tercera["reutilizados"] != 2:
            print(f"FALLO relectura del cambiado -> {tercera}")
            fallos += 1

        liviano = indexar(raiz, espacio, con_texto=False)
        indice_liviano = cargar(Path(liviano["indice"]))
        if any(entrada["texto"] for entrada in indice_liviano["archivos"] if entrada["documento"]):
            print("FALLO --sin-texto -> quedó texto en el índice")
            fallos += 1

        con_todo = indexar(raiz, espacio, todo=True)
        if con_todo["total"] != 4:
            print(f"FALLO --todo -> el .exe no entró: {con_todo}")
            fallos += 1

        # --con-ocr con OCR simulado: el escaneado gana texto_ocr buscable.
        pdf_falso = raiz / "FOLDER 2" / "escaneo.pdf"
        pdf_falso.write_bytes(b"%PDF-falso-sin-texto")
        leer_real = lector.leer
        ocr_real = mod_ocr.ocr
        lector.leer = lambda ruta: {  # type: ignore[assignment]
            "formato": "pdf",
            "metadatos": {},
            "paginas": [{"numero": 1, "texto": ""}],
            "texto": "",
            "aviso": "el PDF no tiene texto extraíble: parece escaneado.",
            "ok": True,
            "ruta": ruta.name,
            "bytes": 10,
        }
        mod_ocr.ocr = lambda ruta, **kwargs: {  # type: ignore[assignment]
            "ok": True,
            "ruta": ruta.name,
            "bytes": 10,
            "formato": "pdf",
            "metadatos": {"ocr": "tesseract"},
            "paginas": [{"numero": 1, "texto": "CONTRATO FAKE POR OCR"}],
            "texto": "CONTRATO FAKE POR OCR",
        }
        try:
            con_ocr_resumen = indexar(raiz, espacio, con_ocr=True)
        finally:
            lector.leer = leer_real  # type: ignore[assignment]
            mod_ocr.ocr = ocr_real  # type: ignore[assignment]
        if con_ocr_resumen.get("con_ocr") != 1:
            print(f"FALLO --con-ocr -> no quedó texto_ocr: {con_ocr_resumen}")
            fallos += 1
        indice_ocr = cargar(Path(con_ocr_resumen["indice"]))
        por_ruta_ocr = {e["ruta"]: e for e in indice_ocr["archivos"]}
        if por_ruta_ocr.get("FOLDER 2/escaneo.pdf", {}).get("texto_ocr") != "CONTRATO FAKE POR OCR":
            print(f"FALLO --con-ocr -> texto_ocr ausente: {por_ruta_ocr.get('FOLDER 2/escaneo.pdf')}")
            fallos += 1
        # Cambiar de modo invalida el incremental: no se reutiliza un índice sin OCR.
        sin_ocr = indexar(raiz, espacio, con_ocr=False)
        if sin_ocr.get("reutilizados"):
            print(f"FALLO cambio de modo OCR -> se reutilizó: {sin_ocr}")
            fallos += 1

    if fallos:
        print(f"\nselftest del indexador: {fallos} fallo(s)")
        return 1
    print("selftest del indexador: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
