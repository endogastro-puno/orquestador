#!/usr/bin/env python3
"""Pasa OCR a un PDF escaneado o a una imagen y devuelve su texto.

Es el cierre del mapa: el índice ya encuentra los PDF escaneados
(`escaneado: true`); este comando los **lee**. Convierte cada página en
imagen (`pdf2image` + `pdftoppm`) y le extrae el texto (`pytesseract` +
binario Tesseract). Para imágenes directas (`.png`, `.jpg`, etc.) salta la
conversión y va directo al OCR.

Cadena necesaria (ver `INSTALACION.md`, sección OCR):

* binario `tesseract` (`winget install tesseract-ocr.tesseract`);
* `python -m pip install pytesseract pillow` (Pillow ya viene en
  `requirements.txt`);
* sólo para PDF: `pdf2image` (ya en `requirements.txt`) + `pdftoppm`
  (Poppler).

Sin esa cadena no hay texto inventado: el comando falla (código 1) diciendo
exactamente qué falta. Si el OCR corre pero no reconoce nada, devuelve el
aviso y sale con código 2, como un PDF escaneado en `leer_documento.py`.

Uso::

    python herramientas/scripts/ocr_documento.py expediente-escaneado.pdf --texto
    python herramientas/scripts/ocr_documento.py foto.png --json
    python herramientas/scripts/ocr_documento.py escaneo.pdf --salida transcripcion.txt

`--salida` guarda la transcripción completa en `<espacio>/entregables/` (un
archivo nuevo; nunca sobrescribe). Sin `--salida` no escribe nada.

Códigos de salida: ``0`` con texto, ``2`` OCR sin texto reconocible (aviso
en stderr), ``1`` error (ruta, dependencias, salida inválida).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace as ws  # noqa: E402

EXTENSIONES_IMAGEN = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")
EXTENSIONES_SALIDA = (".txt", ".md")

COMO_INSTALAR = {
    "tesseract": "winget install tesseract-ocr.tesseract",
    "pytesseract": "python -m pip install pytesseract",
    "pdf2image": "python -m pip install -r requirements.txt  (pdf2image)",
    "Pillow": "python -m pip install -r requirements.txt  (Pillow)",
    "pdftoppm": "winget install oschwartz10612.Poppler  (Poppler trae pdftoppm)",
}


def _hay_modulo(nombre: str) -> bool:
    """True si el módulo ya está importado o se puede importar.

    Mirar `sys.modules` primero hace que los fakes de `selftest` y de las
    pruebas (que sustituyen el módulo en `sys.modules`) cuenten como
    presentes, como un módulo real ya importado.
    """
    if sys.modules.get(nombre) is not None:
        return True
    try:
        import importlib.util
    except ImportError:
        return False
    try:
        return importlib.util.find_spec(nombre) is not None
    except (ImportError, ValueError):
        return False


def verificar_cadena(es_pdf: bool) -> list[tuple[str, str]]:
    """Devuelve la lista de (nombre, cómo instalar) faltantes. Vacía = lista."""
    faltantes: list[tuple[str, str]] = []
    if not _hay_modulo("pytesseract"):
        faltantes.append(("pytesseract (puente Python → Tesseract)", COMO_INSTALAR["pytesseract"]))
    if not _hay_modulo("PIL"):
        faltantes.append(("Pillow (imágenes)", COMO_INSTALAR["Pillow"]))
    if es_pdf and not _hay_modulo("pdf2image"):
        faltantes.append(("pdf2image (PDF → imágenes)", COMO_INSTALAR["pdf2image"]))

    import shutil

    if shutil.which("tesseract") is None:
        faltantes.append(("binario Tesseract", COMO_INSTALAR["tesseract"]))
    if es_pdf and shutil.which("pdftoppm") is None:
        faltantes.append(("pdftoppm (Poppler)", COMO_INSTALAR["pdftoppm"]))
    return faltantes


def _texto_ocr(imagen, idioma: str) -> tuple[str, str]:
    """OCR de un objeto imagen. Devuelve (texto, idioma_usado).

    Intenta el idioma pedido y, si Tesseract no trae esos datos, reintenta con
    su idioma por defecto antes de rendirse.
    """
    import pytesseract  # type: ignore

    try:
        texto = (pytesseract.image_to_string(imagen, lang=idioma) or "").strip()
        return texto, idioma
    except Exception as error:
        mensaje = str(error).lower()
        if "load language" in mensaje or "traineddata" in mensaje:
            texto = (pytesseract.image_to_string(imagen) or "").strip()
            return texto, "por-defecto"
        raise


def ocr_imagen(ruta: Path, idioma: str = "spa") -> dict:
    """OCR de una imagen directa. Falla accionable si falta la cadena."""
    faltantes = verificar_cadena(es_pdf=False)
    if faltantes:
        detalle = "; ".join(f"{nombre}: {como}" for nombre, como in faltantes)
        raise ValueError(f"falta la cadena OCR — {detalle}")
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError:
        raise ValueError(
            "leer con OCR necesita 'pytesseract' y 'Pillow': "
            "python -m pip install pytesseract pillow"
        ) from None

    try:
        with Image.open(ruta) as imagen:
            pixeles = f"{imagen.width}x{imagen.height}"
            try:
                texto, usado = _texto_ocr(imagen, idioma)
            except pytesseract.TesseractNotFoundError:
                raise ValueError(
                    "no se encuentra el binario 'tesseract': "
                    f"{COMO_INSTALAR['tesseract']}"
                ) from None
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(f"no se pudo leer la imagen {ruta.name}: {error}") from None

    resultado = {
        "formato": ruta.suffix.lower().lstrip("."),
        "metadatos": {"ocr": "tesseract", "idioma": usado, "pixeles": pixeles},
        "paginas": [{"numero": 1, "texto": texto}],
        "texto": texto,
    }
    if not texto:
        resultado["aviso"] = (
            "el OCR no reconoció texto: puede ser una imagen vacía, borrosa o "
            "con letra que Tesseract no reconoce. Probá con una imagen más nítida."
        )
    return resultado


def ocr_pdf(
    ruta: Path, idioma: str = "spa", dpi: int = 300, max_paginas: int = 0
) -> dict:
    """OCR de un PDF página por página. Falla accionable si falta la cadena."""
    faltantes = verificar_cadena(es_pdf=True)
    if faltantes:
        detalle = "; ".join(f"{nombre}: {como}" for nombre, como in faltantes)
        raise ValueError(f"falta la cadena OCR — {detalle}")
    try:
        import pytesseract  # type: ignore
        from pdf2image import convert_from_path  # type: ignore
    except ImportError:
        raise ValueError(
            "OCR de PDF necesita 'pdf2image', 'pytesseract' y 'Pillow': "
            "python -m pip install -r requirements.txt && python -m pip install pytesseract"
        ) from None

    try:
        imagenes = convert_from_path(str(ruta), dpi=dpi)
    except Exception as error:
        mensaje = str(error).lower()
        if "poppler" in mensaje or "pdftoppm" in mensaje:
            raise ValueError(
                "no se encuentra 'pdftoppm' (Poppler): "
                f"{COMO_INSTALAR['pdftoppm']}"
            ) from None
        raise ValueError(f"no se pudo convertir el PDF {ruta.name}: {error}") from None

    if max_paginas > 0:
        imagenes = imagenes[:max_paginas]

    paginas: list[dict] = []
    idioma_usado = idioma
    try:
        for numero, imagen in enumerate(imagenes, start=1):
            texto, idioma_usado = _texto_ocr(imagen, idioma)
            paginas.append({"numero": numero, "texto": texto})
    except pytesseract.TesseractNotFoundError:
        raise ValueError(
            f"no se encuentra el binario 'tesseract': {COMO_INSTALAR['tesseract']}"
        ) from None

    texto = "\n\n".join(pagina["texto"] for pagina in paginas).strip()
    resultado = {
        "formato": "pdf",
        "metadatos": {
            "ocr": "tesseract",
            "idioma": idioma_usado,
            "dpi": str(dpi),
            "paginas": str(len(paginas)),
        },
        "paginas": paginas,
        "texto": texto,
    }
    if not texto:
        resultado["aviso"] = (
            "el OCR no reconoció texto en ninguna página: el escaneo puede "
            "estar borroso, chueco o con resolución muy baja. Probá con --dpi 400."
        )
    return resultado


def ocr(
    ruta: Path, idioma: str = "spa", dpi: int = 300, max_paginas: int = 0
) -> dict:
    """Pasa OCR a un PDF o imagen y devuelve el contrato de salida."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise ValueError(f"no existe el archivo: {ruta}")
    extension = ruta.suffix.lower()
    if extension == ".pdf":
        resultado = ocr_pdf(ruta, idioma=idioma, dpi=dpi, max_paginas=max_paginas)
    elif extension in EXTENSIONES_IMAGEN:
        if max_paginas > 0:
            raise ValueError("--paginas sólo aplica a PDF, no a imágenes")
        resultado = ocr_imagen(ruta, idioma=idioma)
    else:
        raise ValueError(
            f"OCR no soporta '{extension}'. Válidos: .pdf y {', '.join(EXTENSIONES_IMAGEN)}"
        )
    try:
        referencia = ruta.resolve().relative_to(ws.RAIZ).as_posix()
    except ValueError:
        referencia = ruta.resolve().as_posix()
    return {
        "ok": True,
        "ruta": referencia,
        "bytes": ruta.stat().st_size,
        **resultado,
    }


def guardar_salida(texto: str, salida: Path, espacio: Path) -> Path:
    """Guarda la transcripción: dentro de entregables, archivo nuevo, sin pisar.

    Una ruta relativa se entiende dentro de `entregables/`; una absoluta debe
    estar ahí también. El archivo no puede existir.
    """
    destino = Path(salida).expanduser()
    base = (Path(espacio) / "entregables").resolve()
    if not destino.is_absolute():
        destino = (base / destino).resolve()
    else:
        destino = destino.resolve()
    try:
        destino.relative_to(base)
    except ValueError:
        raise ValueError(
            f"la salida debe estar dentro de {base} "
            "(la zona de entregables del espacio de trabajo)"
        ) from None
    if destino.suffix.lower() not in EXTENSIONES_SALIDA:
        raise ValueError(
            f"la salida debe ser {', '.join(EXTENSIONES_SALIDA)}; "
            f"pediste '{destino.suffix or '(sin extensión)'}'"
        )
    if destino.exists():
        raise ValueError(
            f"ya existe {destino.name}: nunca se sobrescribe un entregable"
        )
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    return destino


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("ruta", nargs="?", help="PDF escaneado o imagen a leer con OCR")
    parser.add_argument("--json", action="store_true", help="resultado completo como JSON")
    parser.add_argument("--texto", action="store_true", help="imprime sólo el texto plano")
    parser.add_argument(
        "--max-caracteres",
        type=int,
        default=0,
        help="recorta el texto en la salida (0 = sin límite)",
    )
    parser.add_argument("--idioma", default="spa", help="idiomas Tesseract (por defecto: spa)")
    parser.add_argument("--dpi", type=int, default=300, help="resolución del render del PDF (por defecto: 300)")
    parser.add_argument(
        "--paginas",
        type=int,
        default=0,
        help="sólo las primeras N páginas del PDF (0 = todas)",
    )
    parser.add_argument("--salida", help="ruta del .txt/.md a crear dentro de entregables/")
    parser.add_argument("--selftest", action="store_true", help="prueba de humo; no toca nada")
    ws.agregar_argumento(parser)
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.ruta:
        parser.error("hace falta la ruta: el PDF escaneado o la imagen a leer")

    if args.dpi <= 0:
        print("ERROR: --dpi debe ser mayor que 0", file=sys.stderr)
        return 1
    if args.paginas < 0:
        print("ERROR: --paginas no puede ser negativo", file=sys.stderr)
        return 1

    try:
        resultado = ocr(
            Path(args.ruta).expanduser(),
            idioma=args.idioma,
            dpi=args.dpi,
            max_paginas=args.paginas,
        )
    except ValueError as error:
        if args.json:
            print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.salida:
        espacio = ws.resolver(args.workspace)
        try:
            destino = guardar_salida(resultado["texto"], Path(args.salida), espacio)
        except ValueError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
        resultado["salida"] = str(destino)

    # Un solo lugar aplica el recorte, como en leer_documento.py.
    texto = resultado["texto"]
    recortado = False
    if args.max_caracteres > 0 and len(texto) > args.max_caracteres:
        texto = texto[: args.max_caracteres]
        recortado = True

    aviso = resultado.get("aviso")
    if args.json:
        resultado["texto"] = texto
        if recortado:
            resultado["truncado"] = True
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    elif args.texto:
        print(texto)
    else:
        print(f"OCR  {resultado['ruta']}  ({resultado['bytes']} bytes)")
        for clave, valor in resultado.get("metadatos", {}).items():
            print(f"  {clave}: {valor}")
        if "paginas" in resultado:
            print(f"  páginas: {len(resultado['paginas'])}")
        print(f"\n{texto}")
        if recortado:
            print(
                f"[... texto recortado a {args.max_caracteres} caracteres; "
                "subí --max-caracteres o usá --texto para verlo completo]"
            )
        if resultado.get("salida"):
            print(f"\nTranscripción guardada en: {resultado['salida']}")

    if aviso:
        print(f"AVISO: {aviso}", file=sys.stderr)
        return 2
    return 0


def selftest() -> int:
    """Prueba de humo con fakes (sin Tesseract ni Poppler); no toca nada."""
    fallos = 0
    import tempfile
    import types

    # Fakes: módulos reales en sys.modules que sustituyen la cadena OCR.
    class _TesseractNotFoundError(Exception):
        pass

    class _FakeImagen:
        def __init__(self, nombre="pagina"):
            self.nombre = nombre
            self.width = 100
            self.height = 100

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    fake_pytesseract = types.ModuleType("pytesseract")
    fake_pytesseract.TesseractNotFoundError = _TesseractNotFoundError  # type: ignore[attr-defined]
    fake_pytesseract.image_to_string = staticmethod(  # type: ignore[attr-defined]
        lambda imagen, lang=None: f"TEXTO-FAKE[{getattr(imagen, 'nombre', 'pagina')}]"
    )
    fake_pil = types.ModuleType("PIL")
    fake_pil_image = types.ModuleType("PIL.Image")
    fake_pil_image.open = staticmethod(lambda ruta: _FakeImagen(nombre=Path(ruta).name))  # type: ignore[attr-defined]
    fake_pil.Image = fake_pil_image  # type: ignore[attr-defined]
    fake_pdf2image = types.ModuleType("pdf2image")
    fake_pdf2image.convert_from_path = staticmethod(  # type: ignore[attr-defined]
        lambda ruta, dpi=300: [_FakeImagen("p1"), _FakeImagen("p2")]
    )

    fakes = {
        "pytesseract": fake_pytesseract,
        "PIL": fake_pil,
        "PIL.Image": fake_pil_image,
        "pdf2image": fake_pdf2image,
    }
    reales = {nombre: sys.modules.get(nombre) for nombre in fakes}
    sys.modules.update(fakes)

    # which() debe ver los binarios para que verificar_cadena pase.
    import shutil as _shutil

    which_real = _shutil.which
    _shutil.which = lambda nombre: f"/fake/{nombre}"  # type: ignore[assignment]
    try:
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)

            pdf = base / "escaneo.pdf"
            pdf.write_bytes(b"%PDF-fake")
            resultado = ocr(pdf)
            if len(resultado["paginas"]) != 2 or "TEXTO-FAKE[p1]" not in resultado["texto"]:
                print(f"FALLO ocr(pdf) con fakes -> {resultado}")
                fallos += 1

            imagen = base / "foto.png"
            imagen.write_bytes(b"PNG-fake")
            resultado_img = ocr(imagen)
            if resultado_img["paginas"][0]["texto"] != "TEXTO-FAKE[foto.png]":
                print(f"FALLO ocr(imagen) con fakes -> {resultado_img}")
                fallos += 1

            # --paginas recorta; --salida guarda dentro de entregables.
            resultado_corto = ocr(pdf, max_paginas=1)
            if len(resultado_corto["paginas"]) != 1:
                print(f"FALLO --paginas -> {resultado_corto}")
                fallos += 1

            espacio = base / "espacio"
            destino = guardar_salida("hola", Path("salida.txt"), espacio)
            if destino != (espacio.resolve() / "entregables" / "salida.txt"):
                print(f"FALLO guardar_salida() -> {destino}")
                fallos += 1
            try:
                guardar_salida("otra", Path("salida.txt"), espacio)
            except ValueError:
                pass
            else:
                print("FALLO guardar_salida() -> sobrescribió")
                fallos += 1
            try:
                guardar_salida("x", Path("/otra/cosa.txt"), espacio)
            except ValueError:
                pass
            else:
                print("FALLO guardar_salida() -> aceptó ruta fuera de entregables")
                fallos += 1
    finally:
        for nombre, modulo in reales.items():
            if modulo is None:
                sys.modules.pop(nombre, None)
            else:
                sys.modules[nombre] = modulo
        _shutil.which = which_real  # type: ignore[assignment]

    if fallos:
        print(f"\nselftest de OCR: {fallos} fallo(s)")
        return 1
    print("selftest de OCR: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
