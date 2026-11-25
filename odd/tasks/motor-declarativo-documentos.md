# Motor declarativo de documentos

Objetivo: reemplazar los scripts descartables por un generador único guiado por specs, y probarlo con un Plan Operativo y Presupuesto.
Rama: `main` (repo solitario, commits por unidad de trabajo). Entrega: `ask-on-risk`. Verificación: `python -m unittest discover -s herramientas/tests`.

## Specs

**S1** — "OK, PREPARA TODO, PROBAREMOS CON OTRO DOCUMENTO DESPUES"
Un motor declarativo reutilizable: cada tipo se describe en un archivo de spec, no en código ad-hoc.

**S2** — "CREA UN DOCUMENTO DE Plan Operativo y presupuestos PARA KILOCLINIC. WORD"
Nuevo tipo `plan-operativo` con salida `.docx`. Debe generarse **a través del motor**, no con un JS descartable.

**S3** — "Sí, ficticia"
KILOCLINIC es ficticia; se inventan razón social, periodo, metas, actividades y partidas. El archivo queda marcado como demostración.

**S4** — "ES NORMAL QUE DEMORES TANTO EN GENERAR UN DOCUMENTO ?"
La generación debe ser rápida y repetible: el costo se paga una vez en la estructura, no en cada documento.

**S5** — "OK, TEN EN CUENTA QUE EL USUARIO VA QUERER PROBABLEMNENTE DOCUMENTOS QUE NO TENEMOS, ENTONCES TENDRIAS QUE GENERAR ESOS NUEVOS SCRIPTS, VERDAD ?"
Agregar un tipo nuevo debe costar un spec (y un contrato si trae datos nuevos), no cientos de líneas de código.

**S6** — Invariantes del `AGENTS.md`
Ningún dato de usuario se inventa en documentos reales; el agente no escribe en `usuario/` salvo archivos nuevos en `usuario/entregables/`; ningún dato de empresa se versiona; el generador reside en `herramientas/`.

**S7** — Índice verificable
El índice lleva números de página reales y se calcula desde la estructura declarada, sin depender de que Word actualice campos.

## Tasks

- **T1** (S1, S5, S6) — Formato de spec + contratos nuevos (`actividades`, `partidas`). Inline.
- **T2** (S1, S4, S7) — CLI `generar_documento.py` + renderer `renderizar_docx.js`. Inline.
- **T3** (S1, S7) — Tests RED→GREEN con `unittest`. Inline.
- **T4** (S2, S5) — Catálogo, `AGENTS.md` y README de contratos. Inline.
- **T5** (S2, S3, S7) — Generar el Plan Operativo de KILOCLINIC y verificarlo renderizando. Inline.

Ruta elegida: inline. No hay dos unidades paralelas independientes ni presión de contexto; el mismo autor escribe spec, motor y documento.

## Log

**L1** — "OK, PREPARA TODO, PROBAREMOS CON OTRO DOCUMENTO DESPUES"

**L2** — "CREA UN DOCUMENTO DE Plan Operativo y presupuestos PARA KILOCLINIC. WORD"

**L3** — Pregunta: "¿KILOCLINIC es una empresa ficticia para la prueba, como KURAMED?" — Respuesta: "Sí, ficticia".

**L4** — Verificación previa: 11 tipos declarados, 0 generadores versionados. El MOF se generó con un JS de ~600 líneas en `%TEMP%` con datos incrustados. Ese es el patrón que se elimina.

**L5** — CodeGraph inicializado en el repo (no había `.codegraph/`).

**L6** — T5 verificado: Plan Operativo de KILOCLINIC generado por el motor (`acc12fd`), 9 páginas, índice coincidente con las páginas reales (2, 4, 5, 6, 7, 8, 9), total de presupuesto 456,000.00 / 93,500.00, cero marcadores `PENDIENTE`/`{{`/`TODO`. 26 tests verdes. `verificar_limites.py` OK. Entregable no versionado.

**L7** — Defecto corregido durante T5: las tablas estáticas sobrescribían sus filas ya resueltas con las originales, dejando `{{anio}}` visible en el documento. Regresión agregada al test. Segundo ajuste cosmético en el spec: cabecera «Presupuestado» se partía en dos líneas; se redistribuyeron anchos.

**L8** — Revisión nativa RDD: evaluación `high` (1226 líneas, `process_boundary` por subprocess). Usuario consintió «Revisar este cambio». Los cuatro lentes devolvieron `opencode_review_transport_relay_refused (reason: provider_failed)`; el STATUS de la misma línea reofrece los mismos slots. Sin captura admitida: no hay PASS de revisión que reportar.
