# Contratos de datos

Esta carpeta contiene los **contratos** de la fuente de datos del usuario. Son
nuestros: se versionan, se mantienen y describen qué forma deben tener los archivos
que el usuario completa en `usuario/datos/`.

## La convención de rutas

No hay manifiesto ni configuración: la ruta real se deriva del contrato.

```text
herramientas/contratos/organizacion/entidad.csv.example
                    ↓  (se quita .example, se cambia la raíz)
usuario/datos/organizacion/entidad.csv
```

```text
herramientas/contratos/tablas/tarifas.csv.example
                    ↓
usuario/datos/tablas/tarifas.csv
```

`herramientas/scripts/init_local.py` hace esa copia la primera vez.
`herramientas/scripts/validar_datos.py` compara el archivo real contra el contrato.

## Por qué el contrato vive acá y no junto al dato

Porque tienen dueños distintos. El contrato es nuestro y se versiona; el dato es del
usuario y nunca se versiona. Mezclarlos obligaría a que la zona del usuario contenga
archivos nuestros, y ahí se pierde la frontera.

Consecuencia práctica: **actualizar un contrato nunca altera un dato real**. Si
agregamos una columna al contrato, `validar_datos.py` reporta el archivo del usuario
como desactualizado hasta que la agregue. El orden siempre es: contrato primero, dato
después.

## La cabecera del `.example` ES el esquema

No hay un archivo de esquema aparte. La primera fila de cada `.example` declara las
columnas obligatorias y el validador exige exactamente esas. Agregar una columna al
`.example` cambia el contrato para todos, sin tocar código.

En `entidad.csv` la primera columna declara las **claves obligatorias**.

## Contratos disponibles

| Contrato | Archivo real | Contenido |
| --- | --- | --- |
| `organizacion/entidad.csv.example` | `usuario/datos/organizacion/entidad.csv` | Datos legales, contacto e identidad visual |
| `organizacion/contactos.csv.example` | `usuario/datos/organizacion/contactos.csv` | Directorio interno con roles |
| `organizacion/firmantes.csv.example` | `usuario/datos/organizacion/firmantes.csv` | Quién firma y qué documentos |
| `tablas/servicios.csv.example` | `usuario/datos/tablas/servicios.csv` | Catálogo de servicios con código único |
| `tablas/tarifas.csv.example` | `usuario/datos/tablas/tarifas.csv` | Precios por servicio y vigencia |
| `tablas/horarios.csv.example` | `usuario/datos/tablas/horarios.csv` | Programación de atención |

## Columnas

### `organizacion/entidad.csv` — `clave,valor,descripcion`

Tabla vertical de clave/valor. La columna `descripcion` documenta el campo dentro del
propio archivo: no se borra. La clave `actualizado` registra la fecha de la última
revisión.

Claves obligatorias: `razon_social`, `nombre_comercial`, `ruc`, `tipo_contribuyente`,
`regimen_tributario`, `inicio_actividades`, `partida_registral`, `direccion`,
`distrito`, `provincia`, `departamento`, `pais`, `referencia_domicilio`, `telefono`,
`celular`, `correo`, `sitio_web`, `horario_atencion`, `color_primario`,
`color_secundario`, `tipografia`, `logo_principal`, `logo_secundario`,
`membrete_word`, `membrete_excel`, `pie_de_pagina`, `actualizado`.

### `organizacion/contactos.csv` — `area,cargo,nombre,correo,telefono,rol`

`rol`: `destinatario` | `copia` | `aprobador` | `firmante` | `coordinacion`.

### `organizacion/firmantes.csv` — `nombre_completo,cargo,documento,tipo_firma,alcance,imagen_firma`

- `tipo_firma`: `fisica` | `digital`.
- `alcance`: tipos de documento que puede firmar, separados por `;`
  (por ejemplo `memorandum;circular;informe`).
- `imagen_firma`: ruta relativa dentro de `usuario/recursos/`, o `PENDIENTE`.

### `tablas/servicios.csv` — `codigo,servicio,categoria,duracion_min,preparacion,requiere_ayuno`

`codigo` es la clave primaria. `requiere_ayuno`: `si` | `no`.

### `tablas/tarifas.csv` — `codigo_servicio,precio,moneda,vigencia_desde,vigencia_hasta,observacion`

`codigo_servicio` debe existir en `servicios.codigo` (**integridad referencial**; el
validador la controla). Fechas en `AAAA-MM-DD`. `vigencia_hasta` vacía significa
vigente.

### `tablas/horarios.csv` — `area,dia,hora_inicio,hora_fin,profesional,consultorio`

`dia`: `lunes`..`domingo`. Horas en `HH:MM` (24 h).

## Regla anti-invención

> Un dato que no está en `usuario/datos/` **no existe**.
> Un campo con `PENDIENTE` **no está confirmado**.

El agente lee estos datos antes de redactar. Si el documento necesita un campo que
está `PENDIENTE`, vacío o ausente, **detiene la redacción y pide el dato**. Nunca
completa con supuestos, ejemplos plausibles ni «valores típicos». Un RUC, un precio o
un nombre inventado en un documento oficial es un daño real, no un error cosmético.

El agente tampoco completa los `PENDIENTE` él mismo: eso lo hace el usuario. Si lo
hiciera, la fuente dejaría de ser la voz del usuario.

## Validación

```bash
python herramientas/scripts/validar_datos.py            # errores y advertencias
python herramientas/scripts/validar_datos.py --estricto # falla si queda algún PENDIENTE
```

Qué controla:

1. Que cada contrato tenga su archivo real (si falta, recordá `init_local.py`).
2. Que la cabecera del archivo real coincida con el contrato.
3. Que `entidad.csv` tenga todas las claves obligatorias.
4. Que `tarifas.codigo_servicio` apunte a un `servicios.codigo` existente.
5. Formato de fechas `AAAA-MM-DD` en columnas de vigencia.
6. Celdas `PENDIENTE` (advertencia) y tablas sin filas (advertencia).

Código de salida: `0` sin errores, `1` con errores.

## Qué NO va en la fuente de datos

- Datos de pacientes, historias clínicas, DNI, resultados de estudios o cualquier dato
  sensible. Eso va en `usuario/datos/entrada/`, que es privado y nunca se versiona.
- Textos de documentos. Acá sólo hay datos estructurados; la redacción la produce el
  agente a partir de ellos.
- Precios históricos de un solo documento. Si un precio no aplica a todos los
  documentos, va como observación dentro del documento, no en `tarifas.csv`.
