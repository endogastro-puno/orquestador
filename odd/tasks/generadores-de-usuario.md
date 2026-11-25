# Generadores propios del usuario

Feature doc — objetivo: permitir que el usuario genere **todos** sus documentos
con su propia plantilla, escrita como código (JS o Python), sin que ese código
pase a ser del proyecto.

- Rama: `feature/generadores-usuario`
- Entrega: commits por unidad de trabajo en esta rama (push y PR los decide el usuario)
- Runner de pruebas: `python -m unittest discover -s herramientas/tests -v`

## Specs

- **S1** — "cómo hacemos si el usuario quiere tener una plantilla, y él quiere generar
  todos sus documentos con esa plantilla": el motor debe poder producir **cualquier**
  tipo de documento usando el generador propio del usuario, no sólo los tipos que
  el usuario declare.
- **S2** — "sería un código JS o Python": el generador propio puede estar escrito en
  JavaScript o en Python; el contrato es el mismo para los dos.
- **S3** — "eso le pertenece al usuario, no al proyecto": el código del generador vive
  en la zona `usuario/`, nunca se versiona, el agente nunca lo modifica y el motor
  nunca lo importa (se lo ejecuta como subproceso).
- **S4** — División del trabajo elegida: el motor genérico es dueño del **contenido**
  (resuelve placeholders, valida `PENDIENTE`, expande tablas y bloques); el generador
  propio es dueño del **formato** (membrete, tipografía, color, sellos, firmas).
  Por eso el payload incluye el contenido ya resuelto **y** los datos crudos, para
  que el generador aplique la misma regla de no dejar `PENDIENTE` si usa un campo
  que el motor no usó.
- **S5** — Precedencia de resolución del formato:
  1. generador propio del usuario (si declara el tipo),
  2. plantilla binaria propia del usuario,
  3. plantilla oficial,
  4. membrete declarado en `entidad.csv`,
  5. formato por defecto del motor.
- **S6** — Contrato de invocación: el motor arma un `payload.json` y lo entrega al
  generador; el generador escribe el archivo final en la ruta indicada por el payload
  y termina con código de salida 0. Cualquier otro código es error, con su salida
  estándar mostrada textualmente.
- **S7** — El motor genérico actual no se rompe: sin generador propio se sigue
  usando `renderizar_docx.js` exactamente como antes, y hay una forma explícita de
  forzar ese camino.

## Tasks

| ID | Specs | Ruta | Estado | Evidencia |
|----|-------|------|--------|-----------|
| T1 | S1 S2 S3 | inline | pendiente | `herramientas/scripts/generadores_usuario.py` |
| T2 | S4 S6 | inline | pendiente | `herramientas/scripts/generadores_usuario.py` |
| T3 | S5 S7 | inline | pendiente | `herramientas/scripts/generar_documento.py` |
| T4 | S1 S3 | inline | pendiente | `herramientas/scripts/listar_generadores.py`, `init_local.py`, `verificar_limites.py` |
| T5 | S1 S2 S3 S4 S5 S6 S7 | inline | pendiente | `herramientas/tests/test_generadores_usuario.py` |
| T6 | S1 S2 S3 S4 S5 S6 | inline | pendiente | `herramientas/docs/contrato-generador.md`, `herramientas/ejemplos/generador-ejemplo/` |
| T7 | S3 | inline | pendiente | `AGENTS.md`, `README.md`, `herramientas/docs/limites.md`, `herramientas/docs/flujo-de-trabajo.md`, `herramientas/scripts/README.md` |

## Log

- **L1** (2026-11-25, verbatim) — "NOP, NO ME REFIERO A ESO. OSEA COMO HACEMOS SI EL
  USUARIO QUIERE TENER UNA PLANTILLA, Y EL QUIERE GENERAR TODOS SUS DOCUMENTOS CON ESA
  PLANTILLA, SE ENTIENDE ? SERIA UN CODIGO JS O PYTHON, ENTIENDO Y ESO LE PERTENECE AL
  USUARIO, NO AL PROYECTO"
- **L2** (2026-11-25) — Pregunta abierta resuelta por el usuario: "OK, HAZ LO QUE
  RECOMIENDAS". La recomendación era la opción A: el motor genérico es dueño del
  contenido y el generador propio del usuario aplica el formato. Queda registrada en
  **S4**.
- **L3** (2026-11-25) — Se descartó meter el generador del usuario dentro de
  `herramientas/scripts/`: ese código es del cliente (datos, marcas, lógica propia) y el
  repositorio es público. El proyecto publica sólo el **contrato**; el código viaja en
  `usuario/generadores/`.
- **L4** (2026-11-25) — El ejemplo de generator queda en `herramientas/ejemplos/`, no en
  `herramientas/contratos/`: `init_local.py` copia todo `*.example` de `contratos/` a
  `usuario/datos/`, y un ejecutable no es un contrato de datos.
