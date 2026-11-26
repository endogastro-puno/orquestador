# Primer arranque — que el usuario no arme nada desde cero

Feature doc — objetivo: cerrar la brecha entre "el repositorio está" y "el
usuario puede trabajar". Hasta hoy había que saber que existían
`instalar_todo.py`, `init_local.py` y `nueva_plantilla.py`, y correrlos en ese
orden. Un usuario no técnico se quedaba con carpetas vacías, datos sin copiar y
ni una plantilla. Ahora un solo comando deja todo listo.

- Rama: `main` (flujo directo, sin ramas)
- Entrega: commits por unidad de trabajo; push a `origin/main` al cierre
- Runner: `python -m unittest discover -s herramientas/tests -v`

## Specs

- **S1** — `empezar.py` es la puerta de entrada: revisa el entorno, pregunta si
  instala lo que falta, crea las carpetas de la zona del usuario, copia cada
  contrato a su archivo real y deja **una plantilla base por tipo**. Todo en una
  sola corrida.
- **S2** — Nunca pisa nada del usuario: sólo crea archivos que no existen. Si ya
  hay un dato o una plantilla de un tipo, se respeta y se informa. No completa
  `PENDIENTE` ni inventa datos.
- **S3** — Es idempotente: la segunda corrida no crea nada nuevo y lo dice. Sirve
  para volver a ejecutarlo sin miedo.
- **S4** — `--plan` muestra qué haría (entorno, carpetas, datos, plantillas) sin
  escribir en disco. `--si` no pregunta antes de instalar; `--sin-instalar`
  recorta a estructura, datos y plantillas; `--sin-plantillas` deja sólo
  estructura y datos; `--con-ocr` suma la cadena OCR al instalar.
- **S5** — Funciona en cualquier espacio de trabajo (`--workspace`), igual que el
  resto de las facilidades, y nunca escribe fuera de la zona del usuario.
- **S6** — El menú ofrece la acción 15 y, cuando detecta que falta el primer
  arranque (`datos/organizacion/entidad.csv` ausente), sugiere esa opción al
  abrirse. El menú sigue sin duplicar lógica: corre `empezar.py` como
  subproceso.
- **S7** — Códigos de salida explícitos: `0` todo listo; `1` estructura
  preparada pero falta algo obligatorio del entorno o hubo un error de escritura.
  Mensajes en español neutro, sin rutas absolutas incrustadas ni datos de
  empresa; sólo biblioteca estándar.

## Tasks

| ID | Specs | Ruta | Estado | Evidencia |
|----|-------|------|--------|-----------|
| T1 | S1 S2 S3 S5 S7 | inline | hecho | `herramientas/scripts/empezar.py` (`preparar`, `crear_plantillas`, `datos_pendientes`, `mostrar_plan`, `main`, `selftest`) |
| T2 | S6 | inline | hecho | `herramientas/scripts/menu.py` (acción 15, `necesita_primer_arranque`, sugerencia en `mostrar_menu`) |
| T3 | S1–S7 | inline | hecho | `herramientas/tests/test_empezar.py` (16 pruebas) |
| T4 | S1 S4 S6 | inline | hecho | `README.md`, `INSTALACION.md`, `AGENTS.md`, `habilidades.md`, `scripts/README.md` |

## Log

- **L1** (2026-11-26, verbatim) — "CENTRATE EN DARLE HERRAMIENTAS YA LISTAS AL
  USUARIO Y ASI EL USUARIO EVITE CREAR TODO DESDE CERO EN SU PC".
- **L2** (2026-11-26) — Decisión de alcance: no se agrega un instalador nuevo ni
  se duplica lógica. `empezar.py` orquesta lo que ya existe
  (`verificar_entorno.py`, `instalar_todo.py`, `init_local.py`,
  `nueva_plantilla.py`) y aporta la parte que faltaba: crear las plantillas base
  que ningún script creaba en lote.
- **L3** (2026-11-26) — Defecto destapado por el selftest: la aserción de
  `PENDIENTE` se ejecutaba después de que la prueba misma pisara el único CSV que
  los trae, así que exigía lo contrario de lo que el código hace. Se movió la
  comprobación antes de la escritura de prueba; el comportamiento del script era
  correcto.
- **L4** (2026-11-26) — Verificación observada: 197 pruebas en verde (16 nuevas),
  `--selftest`, menú, motor y `verificar_limites.py` OK. Humo real en un espacio
  temporal: 14 carpetas, 9 datos, 12 plantillas creadas; segunda corrida no creó
  nada y respetó los 9 datos y las 12 plantillas; `--sin-plantillas` dejó
  `propias/` vacía. **Risk:** la instalación automática sigue siendo de Windows
  (avisa en otros sistemas y continúa con la estructura); las plantillas base son
  `.docx`/`.xlsx` sobrios, no el membrete real del usuario, que se instala
  después con `instalar_plantilla.py`.
