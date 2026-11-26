# Índice de documentos — el mapa de la selva de carpetas

Feature doc — objetivo: el usuario destino vive en una **selva de carpetas**
(`FOLDER-PRINCIPAL` con N subcarpetas, el repo adentro de una de ellas) y
trabaja principalmente con **Word y PDF, muchos escaneados**. El agente no
puede recorrer esa selva a pie cada vez que necesita un archivo: hace falta
un **mapa** — un índice de documentos que se construye una vez y se consulta
en milisegundos.

- Rama: `main` (flujo directo, sin ramas)
- Entrega: commits por unidad de trabajo; push a `origin/main` al cierre
- Runner: `python -m unittest discover -s herramientas/tests -v`

## Specs

- **S1** — `indexar_documentos.py --ruta <carpeta>` mapea la carpeta completa
  (subcarpetas incluidas, temporales de Office y carpetas de sistema
  excluidas) y guarda el índice en `<espacio>/indice/`. Acepta también un
  archivo: indexa la carpeta que lo contiene.
- **S2** — Índice **incremental**: re-indexar sólo relee lo nuevo o lo
  cambiado (`bytes` + `mtime`); lo que no cambió se conserva tal cual,
  texto incluido. Volver a indexar la misma raíz es barato.
- **S3** — El índice conoce el formato: páginas, párrafos, tablas, hojas,
  metadatos (título, autor) — y marca **`escaneado: true`** a los PDF sin
  texto extraíble. Encontrar "todos los PDF escaneados" es una consulta, no
  una expedición.
- **S4** — `buscar_documentos.py` consulta el índice sin volver a caminar:
  por nombre y por **contenido**, con filtros `--tipo`, `--carpeta`,
  `--escaneados`. Sin consulta, lista (ej: todos los escaneados). Búsqueda
  sin acentos ni mayúsculas; con snippet cuando el match es del texto.
- **S5** — El texto completo se guarda por defecto (buscar dentro de los
  Word/PDF es lakiller feature); `--sin-texto` arma un índice liviano de
  nombres y metadatos.
- **S6** — Lo que no se puede leer (`.docx` corrupto, imagen sin OCR
  instalado) **no se omite**: queda en el mapa con su error. Mapear es saber
  qué hay, también lo roto.
- **S7** — `--todo` incluye los archivos que no son documentos (`.exe`,
  `.zip`, imágenes sin OCR) como entradas de sólo nombre: la raíz puede
  tener de todo y el mapa no debe ser parcial por omisión silenciosa.
- **S8** — Almacenamiento: `<espacio>/indice/` — nueva carpeta de estructura
  del espacio de trabajo, creada por `init_local.py`, con `.gitkeep`
  versionado. Un JSON por raíz: `<slug>-<hash6>.json`, con su `raiz`
  registrada adentro. Dos raíces con el mismo nombre no se pisan.
- **S9** — El índice es el único archivo que se crea, y en la carpeta
  `indice/`. Los originales jamás se tocan: el mapeo sólo lee.
- **S10** — Ambos comandos aceptan `--workspace`, mensajes en español
  neutro, códigos de salida explícitos y `--selftest` en tempfile.

## Tasks

| ID | Specs | Ruta | Estado | Evidencia |
|----|-------|------|--------|-----------|
| T1 | S8 | inline | hecho | `workspace.py` (SUBCARPETAS con `indice/`), `verificar_limites.py` (inventario), `usuario/indice/.gitkeep`; `init_local.py` la crea por SUBCARPETAS |
| T2 | S1 S2 S3 S5 S6 S7 | inline | hecho | `herramientas/scripts/indexar_documentos.py` (incremental por bytes+mtime, errores en el mapa, `--sin-texto`, `--todo`) |
| T3 | S4 S10 | inline | hecho | `herramientas/scripts/buscar_documentos.py` (nombre y contenido sin tildes, snippet, `--tipo`/`--carpeta`/`--escaneados`, exit 1 sin índice con ayuda) |
| T4 | S1 S4 | inline | hecho | `menu.py` (acciones 12 y 13, `pide_carpeta`/`pide_busqueda`) |
| T5 | S1–S10 | inline | hecho | `herramientas/tests/test_indice.py` (151 pruebas en total) |
| T6 | S1 S4 S6 S8 | inline | hecho | `README.md`, `AGENTS.md` (mapa, permisos, flujo, scripts), `scripts/README.md`, `docs/limites.md` |

## Log

- **L1** (2026-11-26, verbatim) — "SIGUE CHAMBEANDO [...] MIS USUARIOS DESTINO,
  TRABAJARAN PRINCIPALMENTE CON WORDS Y PDFS O PDFS ESCANEADOS [...] AGREGUES
  UN MAPPING [...] TENER NUESTRO INDICE DE ARCHIVOS PARA NOSOTROS PODER BUSCAR
  MAS RAPIDO".
- **L2** (2026-11-26) — Decisiones de estructura: la carpeta `indice/` entra a
  `SUBCARPETAS` (la crea `init_local.py`, la espera `verificar_limites.py`,
  su `.gitkeep` se versiona como los otros 13) en vez de un archivo suelto en
  la raíz del espacio: un usuario puede tener varias raíces mapeadas y cada
  una merece su archivo.
- **L3** (2026-11-26) — El hash de 6 caracteres en el nombre del índice evita
  que dos raíces con el mismo basename (dos `CLIENTES` en discos distintos)
  compartan archivo.
- **L4** (2026-11-26) — Risk: el índice guarda texto completo de documentos
  privados — nunca se versiona (vive en `usuario/indice/`, cubierto por la
  regla de zona) y jamás se imprime una ruta absoluta de la máquina en la
  salida de `buscar_documentos.py`: se muestra relativa a la raíz indexada.
- **L5** (2026-11-26) — El OCR de PDFs escaneados queda **fuera** de este
  feature a propósito: el índice los encuentra y los marca; convertirlos es
  otro contrato (pdf2image + Tesseract, ambos opcionales) con su propio spec.
- **L6** (2026-11-26) — Defecto real destapado por el test y corregido: las
  entradas con error de lectura quedaban sin sello y se re-procesaban en
  cada corrida (contadas como "cambiadas"). El sello ahora sale siempre del
  `stat` del walk, lea o no lea el documento: un archivo roto conserva su
  lugar en el mapa y sólo se reintenta cuando cambia de verdad.
  **Risk:** el índice guarda texto completo de documentos privados — vive en
  `usuario/indice/` (cubierto por la regla de zona, jamás se versiona) y la
  salida por archivo es relativa a su raíz indexada.
- **L7** (2026-11-26) — Verificación observada: 151 pruebas en verde (26
  nuevas); selftests de indexador, buscador y menú en verde;
  `verificar_limites.py` OK con la estructura de 14 carpetas. Recorrido real
  en un temporal: selva `FOLDER-PRINCIPAL/CLIENTES A|B` con un `.docx` real y
  un PDF escaneado; `indexar` los mapeó (escaneados: 1); `buscar "manual de
  organizacion"` encontró el Word por su **contenido** con snippet;
  `--escaneados` listó el PDF marcado "necesita OCR".
