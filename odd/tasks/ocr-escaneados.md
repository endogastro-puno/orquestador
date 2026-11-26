# OCR de escaneados — que los PDF escaneados también se puedan leer y buscar

Feature doc — objetivo: cerrar el círculo del mapa. El índice ya encuentra
los PDF escaneados (`escaneado: true`, `buscar_documentos.py --escaneados`);
falta **leerlos**: pasarles OCR para que su texto también sea buscable y para
entregar una transcripción cuando el usuario la pida.

- Rama: `main` (flujo directo, sin ramas)
- Entrega: commits por unidad de trabajo; push a `origin/main` al cierre
- Runner: `python -m unittest discover -s herramientas/tests -v`

## Specs

- **S1** — `ocr_documento.py <ruta>` pasa OCR a un PDF escaneado o a una
  imagen (`.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`, `.webp`) y
  devuelve texto por página. Contrato de salida idéntico en espíritu a
  `leer_documento.py`: `--json` (completo), `--texto` (plano),
  `--max-caracteres` (recorte en todos los modos). Códigos: `0` con texto,
  `2` sin texto reconocible (aviso en stderr), `1` error.
- **S2** — Sin dependencias no hay texto inventado: si falta `pytesseract`,
  `pdf2image`, `Pillow`, el binario `tesseract` o `pdftoppm`, el comando falla
  (exit 1) con el mensaje exacto de qué instalar (`winget` / `pip`). Nunca
  devuelve texto vacío como si el documento no tuviera nada.
- **S3** — `--salida <ruta>` guarda la transcripción. La ruta debe estar
  dentro de `<espacio>/entregables/` y **no existir** (nunca sobrescribe, como
  `generar_documento.py`). Sin `--salida` no escribe nada.
- **S4** — `indexar_documentos.py --con-ocr` reintenta con OCR los PDF
  escaneados y las imágenes sin texto, y guarda `texto_ocr` en la entrada.
  Si el modo OCR pedido difiere del guardado, se re-procesa (no se reutiliza
  un índice sin OCR como si lo tuviera). El resumen cuenta cuántos quedaron
  con OCR.
- **S5** — `buscar_documentos.py` busca también en `texto_ocr` (`donde: ocr`
  con snippet). `--escaneados` sigue listando los escaneados, tengan o no OCR.
- **S6** — `instalar_todo.py --con-ocr` instala la cadena completa: binario
  Tesseract **y** puente `pytesseract` (`pip install pytesseract`). Hoy el
  binario llegaba pero el puente no: el verificador seguía marcando OCR
  ausente después de instalar.
- **S7** — Catálogo único de habilidades (`herramientas/docs/habilidades.md`):
  qué sabemos hacer, con qué skill y con qué script cada cosa, y qué necesita
  instalado cada formato. `AGENTS.md`, `README.md` y `scripts/README.md` lo
  referencian en vez de duplicar tablas que envejecen por separado.
- **S8** — Todo pasa por `workspace.py`, mensajes en español neutro, códigos
  explícitos, `--selftest` en tempfile, sin rutas absolutas ni datos
  incrustados. Sólo biblioteca estándar salvo la cadena OCR justificada
  (`pytesseract` opcional, `pdf2image`/`Pillow` ya en `requirements.txt`).

## Tasks

| ID | Specs | Ruta | Estado | Evidencia |
|----|-------|------|--------|-----------|
| T1 | S1 S2 S3 S8 | inline | hecho | `herramientas/scripts/ocr_documento.py` (OCR PDF/imagen, `--salida` en entregables, códigos 0/2/1) |
| T2 | S4 S8 | inline | hecho | `herramientas/scripts/indexar_documentos.py` (`--con-ocr`, `texto_ocr`/`ocr_error`, re-proceso al cambiar de modo) |
| T3 | S5 | inline | hecho | `herramientas/scripts/buscar_documentos.py` (`donde: ocr` con snippet, etiqueta `match en OCR`) |
| T4 | S6 | inline | hecho | `herramientas/scripts/instalar_todo.py` (`--con-ocr` instala binario + `pytesseract`; fix doc `--sin-ocr` inexistente) |
| T5 | S1–S6 S8 | inline | hecho | `herramientas/tests/test_ocr.py` (171 pruebas en total, fakes sin binarios) |
| T6 | S7 | inline | hecho | `herramientas/docs/habilidades.md` + `ocr-de-documentos.md`; referencias en `AGENTS.md`, `README.md`, `scripts/README.md`, `lectura-de-documentos.md`, `INSTALACION.md` |

## Log

- **L1** (2026-11-26, verbatim) — "SIGUE HAZLO [...] YA SEA EN NUESTRO AGENT
  O AGENTS MD O COMO SEA DEBE QUEDAR CLARO QUE HABILIDADES Y HERRAMIENTAS
  TENEMOS".
- **L2** (2026-11-26) — Decisión de alcance: el OCR convierte escaneados en
  texto buscable y en transcripción entregable; no re-arma un PDF con capa de
  texto (otro contrato, con su propio spec). El mapa ya marca los escaneados;
  este feature los vuelve legibles.
- **L3** (2026-11-26) — Entorno real medido: Python 3.15 OK (el fix de ZK
  persiste en registro; el shell viejo del harness conserva el PATH heredado
  y hay que reconstruirlo), `pdf2image`+`Pillow` instalados, `pdftoppm` vía
  MiKTeX, **sin** binario `tesseract` ni módulo `pytesseract`. El diseño
  falla accionable en vez de asumir la cadena instalada.
- **L4** (2026-11-26) — Tests sin binarios reales: `pdf2image` y
  `pytesseract` se sustituyen con fakes en `sys.modules`; así la lógica
  (páginas, recorte, códigos, guardas de salida, integración índice/búsqueda)
  se prueba en CI, donde Tesseract tampoco está.
- **L5** (2026-11-26) — Defectos destapados por los tests y corregidos:
  (1) fakes como clases no engañan a `find_spec` ni al `from PIL import
  Image`: los fakes son `ModuleType` reales y `verificar_cadena` mira
  `sys.modules` primero (`_hay_modulo`); (2) la salida relativa se resolvía
  contra la raíz del espacio en vez de `entregables/`: ahora la relativa se
  entiende dentro de `entregables/`; (3) `ocr --selftest` chocaba con `ruta`
  posicional obligatoria (mismo patrón ya corregido en el indexador);
  (4) doc de `instalar_todo.py` mencionaba `--sin-ocr`, flag que no existe.
- **L6** (2026-11-26) — Verificación observada: 171 pruebas en verde
  (20 nuevas); selftests de OCR, indexador, buscador y menú en verde;
  `verificar_limites.py` OK. Recorrido real en un temporal: selva con
  `.docx` real y PDF escaneado; `indexar --con-ocr` con OCR simulado guardó
  `texto_ocr` y `buscar "contrato"` lo encontró con `donde: ocr`.
  **Risk:** `texto_ocr` vive en `usuario/indice/` (zona del usuario, jamás
  versionado); la transcripción `--salida` sólo sale a `entregables/` nueva.
