# Facilidades para el usuario final

Feature doc — objetivo: que quien instala el repo goce de **todas** las
herramientas sin ser técnico y sin hablar con el agente: leer insumos
(incluidas imágenes), traer su propia plantilla, arrancar una plantilla
nueva y operar todo desde un solo menú.

- Rama: `feature/generadores-usuario`
- Entrega: commits por unidad de trabajo; push y PR los decide el usuario
- Runner: `python -m unittest discover -s herramientas/tests -v`

## Specs

- **S1** — Un menú (`menu.py`) lista y corre todas las facilidades: sin
  recordar comandos, sin leer documentación. Soporta `--opcion N` para uso
  no interactivo y pasa el código de salida del script que corre.
- **S2** — Leer imágenes con OCR: `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`,
  `.bmp`, `.webp` vía Pillow + pytesseract. Contrato idéntico al de los
  otros lectores: sólo lee; si falta la dependencia o el binario, error
  accionable (exit 1); si la imagen no da texto, `aviso` + exit 2.
- **S3** — `instalar_plantilla.py` copia una plantilla que el usuario ya
  tiene (cualquier ruta de su máquina) a `usuario/plantillas/propias/`
  con la convención `<tipo>-<variante>.<ext>`. Es el contrato de
  `init_local.py`: crea un archivo que **no existe**, nunca sobrescribe,
  nunca mueve el original. La colisión se rechaza con mensaje explícito
  (no hay `-v2` silencioso: dos plantillas del mismo tipo confunden la
  precedencia).
- **S4** — `nueva_plantilla.py` crea una plantilla inicial sobria para un
  tipo del catálogo: `.docx` (OOXML mínimo, biblioteca estándar), `.xlsx`
  (`openpyxl`) o `.md`. Sin datos de empresa, sin membrete: es punto de
  partida, no documento terminado. Mismo contrato de no sobrescritura.
- **S5** — El catálogo de tipos y su extensión de plantilla válida vive en
  un solo módulo (`plantillas.py`); `menu.py`, `instalar_plantilla.py` y
  `nueva_plantilla.py` lo comparten. Los tipos declarativos disponibles
  para generar se descubren de `herramientas/contratos/tipos/*.json`, no
  se duplican en código.
- **S6** — Todo pasa por `workspace.py` (`--workspace` incluido), mensajes
  en español neutro, códigos de salida explícitos, `--selftest` en la
  lógica no trivial, y las rutas de la zona del usuario nunca se escriben
  a mano.
- **S7** — Sólo biblioteca estándar, salvo OCR (pytesseract, ya documentado
  como opcional en `INSTALACION.md`) y la plantilla `.xlsx` (`openpyxl`,
  ya declarado en `requirements.txt`). Nada nuevo que instalar para usar
  el menú o copiar plantillas.

## Tasks

| ID | Specs | Ruta | Estado | Evidencia |
|----|-------|------|--------|-----------|
| T1 | S2 | inline | hecho | `herramientas/scripts/leer_documento.py` (7 extensiones de imagen con OCR, exit 2 sin texto) |
| T2 | S3 S5 S6 S7 | inline | hecho | `herramientas/scripts/plantillas.py` + `instalar_plantilla.py` |
| T3 | S4 S5 S6 | inline | hecho | `herramientas/scripts/nueva_plantilla.py` |
| T4 | S1 S5 S6 | inline | hecho | `herramientas/scripts/menu.py` (11 acciones, `--opcion N`, passthrough de exit code) |
| T5 | S1–S7 | inline | hecho | `herramientas/tests/test_facilidades.py` (125 pruebas en total) |
| T6 | S1 S3 S4 S6 | inline | hecho | `AGENTS.md`, `README.md`, `scripts/README.md`, `docs/lectura-de-documentos.md` |

## Log

- **L1** (2026-11-26, verbatim) — "quiero mejorar la app, para que el
  usuario destino que instale esta aplicacion pueda gozar de todas las
  skills y scripts ya listos, como leer docx, leer pdfs, leer img, creacion
  de templates, copia de alguna plantilla del usuario [...] AGREGAR LA
  MAYOR CANTIDAD DE FACILIDADES".
- **L2** (2026-11-26) — Regla 1 de `scripts/README.md` ("nunca escribir en
  `usuario/plantillas/`") se interpreta con su precedente real:
  `init_local.py` crea archivos que no existen en `usuario/datos/`. La
  copia de plantillas sigue ESE contrato y sólo con un `--origen` que el
  usuario pasa explícitamente: el script no descubre ni decide nada solo.
  La regla del README se aclara en vez de relajarse.
- **L3** (2026-11-26) — La plantilla `.docx` inicial se escribe con OOXML
  mínimo en biblioteca estándar (mismo formato que valida
  `test_lectores.py`): crear una plantilla no debe exigir Node ni
  `python-docx`.
- **L4** (2026-11-26) — Colisión de plantilla: se rechaza con mensaje
  explícito en vez de generar `-v2`. Dos archivos del mismo tipo rompen
  la precedencia documentada; un entregable, en cambio, sí puede
  versionarse porque nadie lo resuelve por nombre.
- **L5** (2026-11-26) — Verificación observada: 125 pruebas en verde
  (33 nuevas); selftests de `plantillas.py`, `nueva_plantilla.py` y
  `menu.py` en verde; `verificar_limites.py` OK. Recorrido real en un
  temporal: `init_local` creó 13 carpetas y 9 contratos;
  `nueva_plantilla` generó `oficio-base.docx` legible por
  `leer_documento`; `instalar_plantilla` copió `oficio-vieja.docx` sin
  tocar el original; `menu.py --opcion 4` validó el espacio; el menú
  interactivo corrió y salió limpio con `0`.
- **L6** (2026-11-26) — Detalle de diseño del OCR: la extensión de imagen
  se registra en `LECTORES` **antes** de importar nada, así el error
  "no existe el archivo" (vs. "formato no soportado") demuestra el
  registro sin instalar Tesseract; la prueba del mensaje accionable se
  salta sola si el OCR sí está instalado.
