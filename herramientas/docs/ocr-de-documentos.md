# OCR de documentos escaneados

Los PDF escaneados son fotos: `leer_documento.py` los detecta y avisa, pero
no los lee. Este documento explica cómo volverlos legibles con
`ocr_documento.py` y cómo dejar su texto en el índice para que la búsqueda
los encuentre.

## Cuándo usarlo

- Un PDF que `leer_documento.py` marcó como escaneado (aviso + código 2).
- Una foto de un documento (`.png`, `.jpg`, `.tif`, `.bmp`, `.webp`).
- Querer la transcripción como archivo (`.txt`/`.md` en `entregables/`).
- Querer que un escaneado sea buscable por contenido (vía `--con-ocr`).

## Uso

```bash
python herramientas/scripts/ocr_documento.py expediente-escaneado.pdf --texto
python herramientas/scripts/ocr_documento.py foto.png --json
python herramientas/scripts/ocr_documento.py escaneo.pdf --salida transcripcion.txt
python herramientas/scripts/ocr_documento.py escaneo.pdf --idioma spa --dpi 400 --paginas 5
```

| Opción | Qué hace |
| --- | --- |
| `--json` | Resultado completo: `paginas` (número y texto), `metadatos` (`ocr`, `idioma`, `dpi`), `texto`, y `salida` si se guardó. |
| `--texto` | Sólo el texto plano, para encadenar. |
| `--max-caracteres N` | Recorta en todos los modos (en `--json` agrega `truncado: true`). |
| `--idioma` | Idiomas Tesseract (por defecto `spa`). Si el dato no está instalado, reintenta con el idioma por defecto e informa `idioma: por-defecto` en los metadatos. |
| `--dpi` | Resolución del render del PDF (por defecto 300; 400 si el escaneo salió borroso). |
| `--paginas N` | Sólo las primeras N páginas (0 = todas). Sólo PDF. |
| `--salida <ruta>` | Guarda la transcripción. Relativa = dentro de `entregables/`; absoluta = debe estar ahí. El archivo no puede existir. |

Códigos: `0` con texto, `2` OCR sin texto reconocible (aviso en stderr),
`1` error (ruta, dependencias o salida inválida).

## La cadena OCR (qué instalar)

| Pieza | Se instala con | Para qué |
| --- | --- | --- |
| binario `tesseract` | `winget install tesseract-ocr.tesseract` | El motor OCR |
| `pytesseract` | `python -m pip install pytesseract` | Puente Python → Tesseract |
| `Pillow` | `requirements.txt` | Abrir imágenes |
| `pdf2image` | `requirements.txt` | PDF → imágenes (sólo PDF) |
| `pdftoppm` (Poppler) | `winget install oschwartz10612.Poppler` | Render de páginas (sólo PDF) |

Todo junto, sin pensar:

```bash
python herramientas/scripts/instalar_todo.py --si --con-ocr
```

Sin la cadena no hay texto inventado: el comando falla diciendo exactamente
qué pieza falta y cómo se instala.

## Escaneados buscables: `--con-ocr` del índice

```bash
python herramientas/scripts/indexar_documentos.py --ruta D:\FOLDER-PRINCIPAL --con-ocr
python herramientas/scripts/buscar_documentos.py "cláusula"   # también mira el OCR
```

El índice guarda el texto reconocido en `texto_ocr` y la búsqueda lo
encuentra (`donde: ocr`, con snippet). Cambiar de modo (con/sin OCR)
re-procesa: un índice sin OCR nunca se hace pasar por uno con OCR. Si el OCR
falla para un archivo, queda `ocr_error` en su entrada y el mapa sigue
intacto.

## Reglas

1. **Nunca inventa texto.** Sin dependencias: error accionable. Con OCR pero
   sin reconocimiento: aviso + código 2.
2. **Los originales no se tocan.** El OCR sólo lee; lo único que se escribe
   es la `--salida` pedida (nueva, en `entregables/`) y el `texto_ocr` del
   índice (regenerable).
3. **Un escaneado borroso** no se adivina: se avisa y se sugiere `--dpi 400`
   o una imagen más nítida.
