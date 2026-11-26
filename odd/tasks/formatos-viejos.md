# Formatos viejos de Office — que los `.doc` y `.xls` de años también se lean

Feature doc — objetivo: cerrar el hueco más grande que quedaba en la selva de
carpetas. El usuario real trabaja en administración: junto a los `.docx` y
`.pdf` hay montañas de `.doc` y `.xls` de años anteriores. Hasta hoy
`leer_documento.py` los rechazaba ("formato no soportado") y el índice los
ignoraba, así que ni se leían ni se encontraban por contenido.

- Rama: `main` (flujo directo, sin ramas)
- Entrega: commits por unidad de trabajo; push a `origin/main` al cierre
- Runner: `python -m unittest discover -s herramientas/tests -v`

## Specs

- **S1** — `leer_documento.py` lee `.doc`, `.rtf`, `.odt`, `.xls` y `.ods`
  convirtiéndolos con LibreOffice (`soffice`) a un temporal y delegando en el
  lector OOXML de siempre. También lee `.docm` y `.xlsm` directo (son OOXML).
  El contrato de salida no cambia; `formato` informa la extensión real del
  archivo (`doc`, `xls`, …) y `metadatos.convertido_con` / `convertido_a`
  dicen cómo se leyó.
- **S2** — El original **nunca se modifica**: la conversión escribe sólo en un
  `TemporaryDirectory`. Se verifica con bytes y `mtime` intactos.
- **S3** — Sin LibreOffice no hay texto inventado: error (código 1) que nombra
  la pieza que falta y cómo instalarla (`winget`), con la alternativa de
  guardar como `.docx`/`.xlsx`. Si la conversión falla o tarda más de 180 s,
  error claro con el detalle de LibreOffice; nunca texto vacío.
- **S4** — El índice hereda el soporte sin código nuevo: `LECTORES` incluye las
  extensiones viejas, así que `indexar_documentos.py` los mapea y
  `buscar_documentos.py` los encuentra por contenido. Un `.doc` que no se pudo
  convertir queda en el mapa con su error, como cualquier otro.
- **S5** — Perfil de LibreOffice propio por conversión
  (`-env:UserInstallation`): si el usuario tiene LibreOffice abierto, la
  conversión headless no se cuelga.
- **S6** — Mensajes en español neutro, sin rutas absolutas incrustadas, sin
  datos de empresa; sólo biblioteca estándar (LibreOffice es un binario
  externo, ya exigido por el proyecto para `.docx`/`.xlsx`/`.pdf`).

## Tasks

| ID | Specs | Ruta | Estado | Evidencia |
|----|-------|------|--------|-----------|
| T1 | S1 S2 S3 S5 S6 | inline | hecho | `herramientas/scripts/leer_documento.py` (`LEGACY`, `_soffice`, `_convertir_con_libreoffice`, `leer_legacy`) |
| T2 | S4 | inline | hecho | `herramientas/scripts/indexar_documentos.py` sin cambios: hereda `LECTORES` |
| T3 | S1–S6 | inline | hecho | `herramientas/tests/test_legacy.py` (10 pruebas con fake de `subprocess`) |
| T4 | S1 S2 S4 | inline | hecho | `lectura-de-documentos.md`, `habilidades.md`, `AGENTS.md`, `README.md`, `scripts/README.md`, `INSTALACION.md`, etiqueta del menú |

## Log

- **L1** (2026-11-26, verbatim) — "sigue mejorando el proyecto".
- **L2** (2026-11-26) — Decisión de alcance: no se reescribe un lector binario
  de `.doc`/`.xls` (formato propietario, enorme superficie de error). Se usa
  LibreOffice, que el proyecto ya exige para generar `.docx`/`.xlsx`/`.pdf`, y
  se lee el OOXML resultante. La conversión va a un temporal: el original es
  intocable, igual que en todo el repositorio.
- **L3** (2026-11-26) — Defecto destapado por los tests: `leer()` devolvía el
  `formato` del lector (`docx`), no el del archivo (`docm`). Ahora el formato
  es siempre la extensión real que pasó el usuario; el orden del dict importa
  (`**resultado` antes de `"formato"`).
- **L4** (2026-11-26) — Verificación observada: 181 pruebas en verde (10
  nuevas); humo real con LibreOffice instalado sobre un `.rtf`: `--texto`
  devolvió el texto, `--json` informó `formato: rtf` + `convertido_con:
  libreoffice`, el índice lo mapeó con `convertidos: 1` (y lo dice en pantalla)
  y `buscar "reunion"` lo encontró; el original conservó sus bytes.
  **Risk:** cada `.doc`/`.xls` lanza LibreOffice (segundos por archivo) la
  primera vez; el índice es incremental, así que la segunda pasada no
  reconvierte. Documentado en `lectura-de-documentos.md`.
