# Espacio de trabajo (`--workspace`)

Feature doc — objetivo: que la herramienta se pueda usar con los datos del
usuario **en cualquier carpeta**, no sólo adentro del repositorio. Es el
bloqueante que separa "repo que se clona" de "herramienta que se usa donde sea".

- Rama: `feature/generadores-usuario`
- Entrega: commits por unidad de trabajo; push y PR los decide el usuario
- Runner: `python -m unittest discover -s herramientas/tests -v`

## Specs

- **S1** — "la idea es que sea como un conjunto de herramientas que quien sea que
  descargue este folder / proyecto pueda usarlo donde deseen": los datos del usuario
  pueden vivir fuera del repositorio.
- **S2** — Precedencia fija y explícita: `--workspace` > `ORQUESTADOR_WORKSPACE` >
  `<repo>/usuario`. Sin `--workspace` nada cambia: el comportamiento actual se
  conserva.
- **S3** — El **espacio de trabajo** es la carpeta que contiene `datos/`,
  `plantillas/`, `generadores/`, `recursos/` y `entregables/`. Todos los comandos
  resuelven la zona del usuario por ese módulo, no con rutas sueltas.
- **S4** — Un espacio externo no se versiona en git: `verificar_limites.py` lo
  informa y sigue; la regla de zona no se relaja.
- **S5** — Un espacio externo no puede publicar rutas absolutas de la máquina en la
  salida.

## Tasks

| ID | Specs | Ruta | Estado | Evidencia |
|----|-------|------|--------|-----------|
| T1 | S2 S3 | inline | hecho | `herramientas/scripts/workspace.py` |
| T2 | S1 S3 | inline | hecho | `init_local.py`, `nuevo_entregable.py`, `generar_documento.py`, `validar_datos.py`, `listar_generadores.py`, `verificar_limites.py` |
| T3 | S2 S4 S5 | inline | hecho | `herramientas/tests/test_workspace.py` (92 pruebas en total) |
| T4 | S2 S3 S4 | inline | hecho | `AGENTS.md`, `README.md`, `limites.md`, `flujo-de-trabajo.md`, `scripts/README.md` |

## Log

- **L1** (2026-11-25, verbatim) — "SIGUE Y COMMIT Y PUSH AL FINAL".
- **L2** (2026-11-25) — Se descartó cambiar el espacio por defecto: `usuario/` sigue
  siendo el default para no romper el modelo de dos zonas documentado en `AGENTS.md`.
  `--workspace` es aditivo: quien no lo usa no nota nada.
- **L3** (2026-11-25) — Integridad referencial de `validar_datos.py` pasó a claves
  relativas a la carpeta de datos (`tablas/tarifas.csv`) en vez de a la raíz del
  repositorio: sin eso, apuntar a otro espacio rompía el cruce tarifas-servicios.
- **L4** (2026-11-25) — El contrato del generador acepta `payload["salida"]` absoluta
  sólo cuando el espacio vive fuera del repositorio; adentro sigue siendo relativa a
  la raíz, que es lo que el generador usa como directorio de trabajo.
- **L5** (2026-11-25) — Verificación observada: 92 pruebas en verde; flujo real con
  `--workspace` en un temporal (`init_local` creó 13 carpetas y copió 9 contratos;
  `validar_datos` dio 14 advertencias y 0 errores; `nuevo_entregable` devolvió
  `entregables/word/2026-11-25_informe-de-prueba.docx`; `verificar_limites` informó
  "espacio externo" sin fallar).
