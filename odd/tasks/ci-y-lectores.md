# CI y lectores de documentos

Feature doc — objetivo: que el repositorio se pueda verificar en cualquier
máquina (CI) y que el agente pueda **leer** los insumos reales (Word, PDF,
Excel) en vez de suponerlos.

- Rama: `feature/generadores-usuario`
- Entrega: commits por unidad de trabajo en esa rama; push y PR los decide el usuario
- Runner: `python -m unittest discover -s herramientas/tests -v`

## Specs

- **S1** — "la idea es que sea como un conjunto de herramientas que quien sea que
  descargue este folder / proyecto pueda usarlo donde deseen": el repositorio debe
  poder comprobarse solo, en Linux, macOS y Windows, sin depender de una máquina.
- **S2** — "agrega mas scripts o skills para leer words, leer pdfs, etc.": leer un
  `.docx`, un `.pdf` y un `.xlsx` debe ser un comando, no una suposición del agente.
- **S3** — Un clon limpio tiene la estructura completa de `usuario/`: ninguna carpeta
  esperada puede faltar por no estar versionada.
- **S4** — Leer `.docx` no agrega dependencias: es un ZIP con XML.
- **S5** — Si un formato no se puede leer (PDF escaneado sin OCR, formato no
  soportado), el comando **falla o avisa**; nunca devuelve texto aproximado.
- **S6** — La lectura no modifica nada: sólo abre archivos en modo lectura.

## Tasks

| ID | Specs | Ruta | Estado | Evidencia |
|----|-------|------|--------|-----------|
| T1 | S1 | inline | hecho | `.github/workflows/ci.yml` (ubuntu 3.10/3.13, windows 3.13, macos 3.13) |
| T2 | S1 | inline | hecho | `herramientas/scripts/selftest.py` |
| T3 | S3 | inline | hecho | `.gitkeep` en `usuario/generadores`, `usuario/datos/organizacion`, `usuario/datos/tablas` |
| T4 | S2 S4 S5 S6 | inline | hecho | `herramientas/scripts/leer_documento.py` |
| T5 | S2 S4 S5 S6 | inline | hecho | `herramientas/tests/test_lectores.py` (77 pruebas en total) |
| T6 | S2 | inline | hecho | `herramientas/docs/lectura-de-documentos.md` y referencias en AGENTS/README/INSTALACION |

## Log

- **L1** (2026-11-25, verbatim) — "OK, HAZLO. Y TAMBIEN AGREGA MAS SCRIPTS O SKILLS
  PARA LEER WORDS, LEER PDFS, ETC."
- **L2** (2026-11-25) — Se eligió **script** y no skill para leer: un lector
  determinista se prueba, se encadena y falla con código de salida. Una skill sólo
  describe qué hacer; el parseo de un `.docx` no admite improvisación.
- **L3** (2026-11-25) — `.docx` se lee con `zipfile` + `xml.etree`: sin dependencias.
  `.pdf` y `.xlsx` usan las dependencias que ya estaban en `requirements.txt`
  (`pdfplumber`/`pypdf`, `openpyxl`), con error explícito si faltan.
- **L4** (2026-11-25) — Hallazgo de portabilidad real: en una máquina con varias
  instalaciones de Python, el motor lanzaba al generador con `"python"` del `PATH`.
  Ahora el manifiesto sin `comando` usa `sys.executable`, y el subproceso descarta un
  `PYTHONHOME` heredado. Sin eso, un `PYTHONHOME` viejo rompe el intérprete hijo.
- **L5** (2026-11-25) — Verificación observada: 77 pruebas en verde; `selftest.py`
  con los dos caminos OK en un temporal (renderizador 11 120 bytes, generador propio
  40 bytes); `leer_documento.py` sobre un entregable real de 20 231 bytes devolvió 219
  párrafos, 13 tablas y los metadatos del documento.
