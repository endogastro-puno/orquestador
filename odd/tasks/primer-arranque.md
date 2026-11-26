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
  preparada pero falta algo obligatorio del entorno, no se pudo verificar el
  entorno o hubo un error de escritura. Mensajes en español neutro, sin rutas
  absolutas incrustadas ni datos de empresa; sólo biblioteca estándar.
- **S8** — Windows sin terminal: `EMPEZAR.bat` y `MENU.bat` en la raíz. Doble
  clic, buscan `py -3` y luego `python` **verificando que sea 3.10+**, limpian
  `PYTHONHOME`/`PYTHONPATH` heredados de otra instalación (rompen Python sin
  avisar), pasan los argumentos y hacen `pause` para que el resultado se lea.
  Se versionan con fin de línea CRLF.
- **S9** — Sólo se imprime `TODO LISTO` cuando el entorno quedó verificado y sin
  faltantes; si no se pudo verificar, se dice y el código de salida es `1`.

## Tasks

| ID | Specs | Ruta | Estado | Evidencia |
|----|-------|------|--------|-----------|
| T1 | S1 S2 S3 S5 S7 | inline | hecho | `herramientas/scripts/empezar.py` (`preparar`, `crear_plantillas`, `datos_pendientes`, `mostrar_plan`, `main`, `selftest`) |
| T2 | S6 | inline | hecho | `herramientas/scripts/menu.py` (acción 15, `necesita_primer_arranque`, sugerencia en `mostrar_menu`) |
| T3 | S1–S9 | inline | hecho | `herramientas/tests/test_empezar.py` (23 pruebas) |
| T4 | S1 S4 S6 | inline | hecho | `README.md`, `INSTALACION.md`, `AGENTS.md`, `habilidades.md`, `scripts/README.md` |
| T5 | S8 S9 | inline | hecho | `EMPEZAR.bat`, `MENU.bat`, `.gitattributes`; pruebas de lanzadores y de `TODO LISTO` en `test_empezar.py` |

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
- **L5** (2026-11-26) — El usuario preguntó «¿falta algo?». Faltaba el doble clic:
  el primer paso seguía siendo abrir una terminal. Se agregan `EMPEZAR.bat` y
  `MENU.bat`. Probarlos destapó un caso real: la sesión traía
  `PYTHONHOME=C:\ZK\Python37` y `py -3` arrancaba Python 3.15 con esa raíz, con
  un error fatal de `site`. Los lanzadores ahora limpian `PYTHONHOME`/
  `PYTHONPATH` y verifican `sys.version_info >= (3, 10)` antes de usarlos. Humo
  real con el entorno envenenado: `EMPEZAR.bat --plan` y `MENU.bat --selftest`
  funcionaron igual. De paso, el mensaje final de `empezar.py` se alineó con la
  guía (`TODO LISTO`) y el código de salida pasó a `1` cuando no se pudo
  verificar el entorno.
- **L6** (2026-11-26) — Cierre: el único defecto restante era que un error al
  crear una plantilla se mostraba pero no cambiaba el código de salida (el spec
  S7 promete `1` ante error de escritura). Ahora `plantillas_error` llega al
  resultado, bloquea el `TODO LISTO` y devuelve `1`. Prueba nueva con
  `np.crear` forzado a `OSError`: 204 pruebas en verde.
- **L7** (2026-11-26) — CI en rojo, pero por defectos **preexistentes** de las
  pruebas, no del arranque: `TestResolucion` comparaba `resolver()` (que
  canonicaliza con `.resolve()`) contra la ruta sin resolver, y en macOS
  `/var` → `/private/var`; en Windows el runner usa nombres 8.3 (`RUNNER~1`). Y
  `test_plan_con_ocr_incluye_puente` esperaba código `0` en macOS, donde el
  instalador automático es Windows-only y devuelve `1` a propósito. Se comparan
  rutas resueltas en ambos lados y la prueba del instalador se saltea fuera de
  Windows con motivo explícito.
- **L8** (2026-11-26) — Segundo fallo de CI, también preexistente y sólo en
  Ubuntu: `test_no_duplica_entradas` exigía un `PATH` sin repetidos, pero
  `refrescar_path()` es no-op fuera de Windows y el runner de Linux ya traía un
  duplicado heredado (19 entradas, 18 únicas). Se cambia la aserción al contrato
  real: el refresco no pierde entradas ni **agrega** duplicados, comparando
  contra el estado inicial. Simulado el camino no-Windows: un `PATH` con
  duplicado queda igual tras dos refrescos.
- **L9** (2026-11-26) — Tercer fallo de CI y **este sí era un bug de código**:
  `indexar_documentos.py` recorría con `Path.walk()`, que existe desde Python
  3.12, pero el repositorio declara 3.10+. En Ubuntu 3.10 fallaban 28 pruebas con
  `AttributeError: 'PosixPath' object has no attribute 'walk'`. Se reemplazó por
  `os.walk(raiz)` + `Path(carpeta)` (misma semántica de poda de carpetas).
  Verificado: 204 pruebas y selftest del indexador OK; además se compiló todo
  `herramientas/**/*.py` con `ast.parse(feature_version=(3, 10))` sin errores de
  sintaxis.
