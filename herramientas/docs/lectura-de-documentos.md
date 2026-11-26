# Lectura de documentos

Un documento que el usuario entrega es un **insumo**, no un adorno: si el agente
no lo lee, lo inventa. `leer_documento.py` convierte cualquier insumo en texto y
estructura para trabajar sobre datos reales.

## Formatos

| Formato | Cómo se lee | Dependencia |
| --- | --- | --- |
| `.docx` | OOXML directo (`zipfile` + `xml.etree`) | **ninguna** |
| `.pdf` | `pdfplumber`; si no está, `pypdf` | `requirements.txt` |
| `.xlsx` | `openpyxl`, en modo sólo lectura | `requirements.txt` |
| `.csv` | módulo `csv` | **ninguna** |
| `.md`, `.txt` | lectura directa | **ninguna** |
| `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`, `.webp` | OCR: `Pillow` + `pytesseract` + binario Tesseract | opcional (`INSTALACION.md`) |

Un `.docx` es un ZIP con XML adentro: por eso se lee sin instalar nada. Eso
importa: el formato más común del trabajo administrativo no agrega dependencias
al repositorio.

## Uso

```bash
python herramientas/scripts/leer_documento.py usuario/datos/entrada/informe.docx
python herramientas/scripts/leer_documento.py planilla.xlsx --json
python herramientas/scripts/leer_documento.py contrato.pdf --texto
python herramientas/scripts/leer_documento.py nota.md --max-caracteres 500
python herramientas/scripts/leer_documento.py escaneo.png --texto
```

| Opción | Qué hace |
| --- | --- |
| `--json` | Salida completa y estructurada, para que la use un agente o un script. |
| `--texto` | Sólo el texto plano, para buscar o encadenar. |
| `--max-caracteres N` | Recorta el texto en **todos** los modos: humano, `--texto` y `--json` (ahí agrega `truncado: true`). |

Códigos de salida:

| Código | Significado |
| --- | --- |
| `0` | Leyó y devolvió texto. |
| `2` | Leyó, pero **no hay texto extraíble** (PDF escaneado, imagen sin texto). El aviso va a la salida de error. |
| `1` | Error: no existe, formato no soportado, archivo corrupto o dependencia faltante — incluida la imagen con OCR sin instalar, cuyo mensaje dice qué falta. |

## Contrato de salida (`--json`)

Siempre: `ok`, `formato`, `ruta`, `bytes`, `texto`, `metadatos`.

Según el formato, además:

| Clave | Formato | Contenido |
| --- | --- | --- |
| `parrafos` | `.docx` | Lista de párrafos con texto (sin vacíos). |
| `tablas` | `.docx` | Lista de tablas; cada tabla es una lista de filas de celdas. |
| `paginas` | `.pdf` | Una entrada por página: `numero` y `texto`. |
| `hojas` | `.xlsx` | Una entrada por hoja: `nombre` y `filas`. |
| `filas` | `.csv` | Filas crudas del archivo. |
| `pixeles` | imágenes | En `metadatos`: ancho x alto de la imagen leída. |
| `aviso` | `.pdf`, imágenes | Sólo si no hay texto extraíble. |

`ruta` se informa relativa al repositorio cuando el archivo está adentro; nunca
se filtran rutas absolutas de la máquina.

```json
{
  "ok": true,
  "formato": "docx",
  "ruta": "usuario/datos/entrada/informe.docx",
  "bytes": 20231,
  "metadatos": { "titulo": "Informe", "autor": "ACME", "creado": "2026-11-25T16:13:50Z" },
  "parrafos": ["Primer párrafo", "Segundo"],
  "tablas": [[["Código", "Monto"], ["P-001", "10.00"]]],
  "texto": "Primer párrafo\n\nSegundo"
}
```

## Reglas

1. **Sólo lee.** Nunca modifica el archivo ni escribe nada.
2. **No inventa.** Si no puede leer —PDF escaneado sin OCR, formato no
   soportado— falla o avisa; no devuelve texto aproximado.
3. **PDF escaneado**: un PDF que es una imagen no tiene texto extraíble. El
   comando lo detecta y devuelve un `aviso` explícito; para leerlo hace falta OCR
   (`Tesseract`), que no está instalado por defecto.
4. **Imágenes**: se leen con OCR (`Pillow` + `pytesseract` + binario
   `Tesseract`, opcional). Sin OCR instalado el comando falla con el mensaje
   exacto de qué instalar — nunca devuelve "texto vacío" como si la imagen no
   tuviera nada. Con OCR y sin texto reconocible, devuelve `aviso` y sale con
   código `2`, igual que un PDF escaneado.
5. **Un `.docx` corrupto** falla con error, no con texto vacío.

## Cuándo usarlo

- Antes de redactar: leer el insumo que el usuario dejó en
  `usuario/datos/entrada/`.
- Para verificar un entregable propio: leer el `.docx` generado y comprobar que
  el contenido está donde debe.
- Para extraer tablas de una planilla y cruzarlas contra `usuario/datos/tablas/`.
- Si el PDF es escaneado (aviso + código 2) o el insumo es una foto: pasar a
  `ocr_documento.py` (detalle en `ocr-de-documentos.md`).
