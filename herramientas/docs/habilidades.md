# Habilidades y herramientas

Catálogo único de lo que sabe hacer este repositorio. Si una habilidad no
está acá, no existe: preguntá antes de inventarla. Cada fila dice **con qué
skill** (`.opencode/skills/`, la usa el agente al redactar o generar) y **con
qué script** (`herramientas/scripts/`, lo corre el usuario o el agente en la
terminal) se hace, y qué hay que tener instalado.

El punto de entrada para quien no quiere memorizar nada:

```bash
python herramientas/scripts/menu.py
```

El punto de entrada para quien acaba de clonar el repositorio y no quiere armar
nada a mano —entorno, carpetas, datos base y una plantilla de cada tipo—:

```bash
python herramientas/scripts/empezar.py
```

## Leer: del archivo suelto al texto usable

| Habilidad | Skill | Script | Necesita instalado |
| --- | --- | --- | --- |
| Leer Word, PDF con texto, Excel, CSV, texto e imágenes —incluidos los `.doc`/`.xls` viejos— | — | `leer_documento.py` | `.docx`/`.docm`/`.csv`/`.md`/`.txt`: nada; `.pdf`: `pdfplumber` o `pypdf`; `.xlsx`/`.xlsm`: `openpyxl`; `.doc`/`.xls`/`.rtf`/`.odt`/`.ods`: LibreOffice (`soffice`); imágenes: cadena OCR |
| Leer un PDF escaneado o una foto | `pdf` (extracción y OCR) | `ocr_documento.py` | Tesseract + `pytesseract` + `Pillow`; y para PDF: `pdf2image` + `pdftoppm` |
| Mapear una carpeta completa (el mapa) | — | `indexar_documentos.py [--con-ocr]` | Lo mismo que leer; `--con-ocr` suma la cadena OCR |
| Buscar por nombre y por contenido en el mapa | — | `buscar_documentos.py` | Nada (lee el índice) |

Detalle de lectura: `lectura-de-documentos.md`. Detalle de OCR:
`ocr-de-documentos.md`.

## Plantillas: usar las que ya tenés o arrancar una

| Habilidad | Skill | Script | Necesita instalado |
| --- | --- | --- | --- |
| Traer tu plantilla existente (`<tipo>-<variante>.<ext>`) | — | `instalar_plantilla.py --origen <ruta> --tipo <tipo>` | Nada |
| Crear una plantilla inicial sobria | `docx` (si es `.docx`) | `nueva_plantilla.py --tipo <tipo>` | `.xlsx`: `openpyxl`; lo demás: nada |
| Usar tu plantilla escrita en código (gana siempre) | — (tu código) | `generar_documento.py` la ejecuta como subproceso | Lo que tu código pida |
| Ver qué generadores propios tenés | — | `listar_generadores.py` | Nada |

Contrato del generador en código: `contrato-generador.md`.

## Redactar y generar: del dato al entregable

| Habilidad | Skill | Script | Necesita instalado |
| --- | --- | --- | --- |
| Redactar contenido administrativo (memorándum, informe, acta…) | `internal-comms` | — (redacción del agente) | Nada |
| Redactar un documento largo por iteración | `doc-coauthoring` | — (redacción del agente) | Nada |
| Generar `manual` y `plan-operativo` desde los CSV | `docx` | `generar_documento.py --tipo <tipo>` | Node + `docx` (npm), Pandoc, LibreOffice |
| Armar cualquier `.docx` (membrete, índice, firmas, imágenes) | `docx` | `renderizar_docx.js` (lo llama el motor) | Node + `docx` (npm) |
| Armar planillas con fórmulas y totales | `xlsx` | — (la usa el agente) | `openpyxl`, `pandas`, LibreOffice |
| Armar o convertir PDF (unir, formularios, PDF final) | `pdf` | — (la usa el agente) | `pypdf`, `pdfplumber`, `reportlab`, `pdf2image`, Poppler |
| Reservar la ruta del entregable (`AAAA-MM-DD_slug.ext`, sin pisar) | — | `nuevo_entregable.py --tipo <tipo> --nombre "..."` | Nada |
| Aplicar identidad visual | `brand-guidelines` | — (la usa el agente) | Nada |

Tipos, datos obligatorios y esqueletos: `tipos-de-documento.md`. Flujo de
7 pasos: `flujo-de-trabajo.md`.

## Entorno y cuidado de la frontera

| Habilidad | Script | Necesita instalado |
| --- | --- | --- |
| Ver qué falta instalar (por formato) | `verificar_entorno.py [--formato docx\|xlsx\|pdf]` | Nada |
| Instalar lo que falte (Windows; `--con-ocr` incluye Tesseract + `pytesseract`) | `instalar_todo.py [--plan\|--si] [--con-ocr]` | `winget` |
| Dejar todo listo de una vez: entorno + carpetas + datos + plantillas (`--plan` no escribe) | `empezar.py [--plan\|--si\|--sin-instalar\|--sin-plantillas]` | Nada para la estructura; lo que pida `instalar_todo.py` si decidís instalar |
| Crear tu estructura y tus datos (sin pisar) | `init_local.py` | Nada |
| Validar tus datos contra los contratos | `validar_datos.py [--estricto]` | Nada |
| Comprobar que nada tuyo quedó en git | `verificar_limites.py` | `git` |
| Probar que el motor funciona acá | `selftest.py` | Nada |

Guía de instalación: `INSTALACION.md` en la raíz.

## Qué formato sale de cada tipo

| Tipo | Sale como | Skill principal |
| --- | --- | --- |
| `memorandum`, `circular`, `oficio`, `solicitud`, `constancia`, `acta`, `comunicado` | `.docx` (`.md` si va a seguir iterando) | `internal-comms` + `docx` |
| `informe`, `manual`, `plan-operativo` | `.docx`, `.pdf` final | `internal-comms` + `docx`, `pdf` |
| `reporte`, `cotizacion` | `.xlsx` (cotización también `.docx`) | `xlsx` |

## Reglas que no se negocian

1. Ningún dato se inventa: sale de `usuario/datos/` o lo aporta el usuario.
2. `usuario/` es del usuario: sólo se lee (salvo entregables nuevos e índice
   regenerable). Detalle: `limites.md`.
3. Lo que no se puede leer no se finge: se avisa o se falla con el mensaje
   exacto de qué instalar.
