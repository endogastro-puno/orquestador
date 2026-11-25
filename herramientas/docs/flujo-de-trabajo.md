# Flujo de trabajo

Pipeline obligatorio para producir cualquier documento. Los pasos 1 a 3 son
obligatorios y verificables; los pasos 4 a 7 son la ejecución.

```text
usuario/datos/  →  usuario/generadores/  →  usuario/plantillas/  →  redacción  →  generación  →  verificación  →  entrega
```

Recordá la frontera: todo lo que se lee vive en `usuario/`, y en `usuario/` sólo se
escribe dentro de `usuario/entregables/`.

## Paso 1 — Identificar el tipo de documento

Determiná el `tipo` según `herramientas/docs/tipos-de-documento.md`. Si el pedido
mezcla dos tipos (por ejemplo un informe que además es comunicación externa), elegí el
dominante y decilo explícitamente en la entrega.

**Salida del paso**: `tipo`, formato destino (`.md`, `.docx`, `.xlsx`, `.pdf`) y lista
de datos obligatorios.

## Paso 2 — Verificar la fuente de datos

```bash
python herramientas/scripts/validar_datos.py
```

- Si hay **errores**: la fuente de datos está incompleta o inconsistente. No se
  redacta. Se informa qué falta y se detiene.
- Si hay **advertencias por `PENDIENTE`** en campos que el documento necesita: se
  pregunta por esos campos puntuales.
- Si hay `PENDIENTE` en campos que el documento **no** usa: se continúa y se menciona
  en la entrega que la fuente quedó parcial.

Nunca se completa un `PENDIENTE` con un valor inventado, aunque parezca obvio. Y el
agente tampoco lo completa con el valor correcto: **el dato lo escribe el usuario**.

## Paso 3 — Resolver la plantilla

Orden fijo (ver `herramientas/docs/limites.md`):

1. `usuario/generadores/<nombre>/` — generador propio del usuario, si declara el
   tipo. Es código suyo: se ejecuta, no se edita. Contrato completo en
   `herramientas/docs/contrato-generador.md`.
2. `usuario/plantillas/propias/<tipo>-*`
3. `usuario/plantillas/oficiales/<tipo>-*`
4. Membretes declarados en `usuario/datos/organizacion/entidad.csv`
5. Formato por defecto del motor

Se trabaja siempre sobre una **copia**. La plantilla original no se toca.

Si el usuario tiene un generador propio, el motor resuelve el contenido y se lo
entrega ya resuelto: el generador aplica sólo el formato. Con
`python herramientas/scripts/listar_generadores.py` se ve qué generadores hay y
qué tipos cubren.

## Paso 4 — Redactar

- Contenido con `internal-comms` (documentos administrativos) o `doc-coauthoring`
  (documentos largos que el usuario quiere iterar).
- Estructura según el esqueleto del tipo en `herramientas/docs/tipos-de-documento.md`.
- Todos los datos duros (nombres, cargos, RUC, direcciones, precios, horarios)
  provienen de `usuario/datos/`. La redacción no agrega hechos nuevos.

## Paso 5 — Generar el archivo

1. Resolvé la ruta con el script, nunca a mano:

   ```bash
   python herramientas/scripts/nuevo_entregable.py --tipo word --nombre "Memorándum de horarios"
   ```

   Devuelve `usuario/entregables/word/AAAA-MM-DD_memorandum-de-horarios.docx` y
   resuelve colisiones de nombre.

2. Generá el archivo con la skill correspondiente (`docx`, `xlsx`, `pdf`) sobre esa
   ruta exacta.

Nunca sobrescribas un entregable existente. Si el nombre está ocupado, el script
propone `-v2`; usalo.

## Paso 6 — Verificar antes de entregar

Checklist mínimo:

| # | Control | Cómo |
| --- | --- | --- |
| 1 | El archivo existe y abre | abrir/leer el archivo generado |
| 2 | Tiene el nombre y la ubicación correctos | `AAAA-MM-DD_slug.ext` dentro de `usuario/entregables/<tipo>/` |
| 3 | No quedan marcadores sin resolver | buscar `PENDIENTE`, `<correlativo>`, `TODO`, `XXX` |
| 4 | Las cifras coinciden con la fuente | comparar contra `usuario/datos/tablas/` |
| 5 | Los nombres y cargos coinciden | comparar contra `contactos.csv` / `firmantes.csv` |
| 6 | El formato es el pedido | `.docx` vs `.md` vs `.xlsx` |
| 7 | El logo y el membrete son los correctos | según `entidad.csv` |

Si falla cualquier control, se corrige antes de entregar. Los controles 3 a 5 son los
que atrapan errores reales: documento con `PENDIENTE` en el cuerpo, cifra que no
cierra, cargo desactualizado.

## Paso 7 — Entregar

En la respuesta final se informa:

- Ruta del archivo generado.
- Tipo de documento y formato.
- Qué datos se usaron y de qué archivo salieron.
- Qué quedó pendiente (campos `PENDIENTE` que afectan al documento, si hubo).
- Riesgo del cambio, cuando corresponda.

## Casos de error

| Situación | Qué hace el agente |
| --- | --- |
| La zona del usuario no existe | Ejecuta `init_local.py`, informa y pide los datos mínimos |
| Falta un dato obligatorio | Pregunta por ese dato y se detiene |
| El dato existe pero es `PENDIENTE` | Pregunta; no asume y no lo completa él |
| El validador reporta error de integridad | Informa el error de la fuente y no redacta |
| No hay plantilla ni membrete | Usa el formato por defecto y lo menciona |
| El tipo de documento no está en el catálogo | Propone el tipo más cercano y confirma antes de generar |
| El formato pedido no admite el contenido | Avisa y propone alternativa (por ejemplo tabla → `.xlsx`) |
| El nombre de archivo ya existe | Usa la versión `-v2` que propone el script; no sobrescribe |
| El generador propio del usuario falla | Se muestra su error textual; no se edita su código. Se propone el arreglo y el usuario decide |

## Bitácora de entregables

Los entregables están fuera de git, así que la trazabilidad vive en el nombre del
archivo y en la respuesta al usuario. Si el usuario pide historial, se puede crear
`usuario/entregables/registro.md` (local, no versionado) con una fila por documento:

```markdown
| fecha | tipo | archivo | solicitado por | observaciones |
| --- | --- | --- | --- | --- |
```

El agente sólo crea ese archivo si el usuario lo pide.
