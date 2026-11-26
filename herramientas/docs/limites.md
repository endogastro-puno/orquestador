# Límites de zona

Este repositorio tiene **dos zonas con dueños distintos**. La frontera no es una
convención de estilo: es una regla operativa que se verifica con un script.

```text
orquestador/
├── usuario/          ← ZONA DEL USUARIO. Nunca se toca.
├── herramientas/     ← NUESTRA ZONA. Se mantiene y se versiona.
├── .opencode/        ← NUESTRA ZONA. Skills instaladas.
├── odd/              ← NUESTRA ZONA. Registro de decisiones de desarrollo.
├── AGENTS.md         ← NUESTRA ZONA. Reglas del agente.
└── README.md         ← NUESTRA ZONA.
```

## Regla de oro

> **Nuestro trabajo termina en `herramientas/`.**
> En `usuario/` sólo damos facilidades: carpetas creadas, contratos, validación y
> resolución de rutas. El contenido lo produce el usuario.

Si una herramienta necesita un dato que vive en `usuario/`, **lo lee o lo pide**.
Nunca lo escribe, lo deduce ni lo inventa.

## Qué puede hacer el agente en cada carpeta

| Ruta | Permiso del agente | Detalle |
| --- | --- | --- |
| `usuario/datos/` | **Sólo lectura** | Los `PENDIENTE` los completa el usuario, no el agente |
| `usuario/datos/entrada/` | **Sólo lectura** | Insumos crudos: Excel, PDF, texto |
| `usuario/plantillas/propias/` | **Sólo lectura** | Precedencia máxima al generar |
| `usuario/plantillas/oficiales/` | **Sólo lectura** | Membretes y formatos de la organización |
| `usuario/generadores/` | **Sólo lectura** | Código del usuario: su plantilla escrita en Python o JS. Se ejecuta, no se edita |
| `usuario/recursos/logos/` | **Sólo lectura** | Se insertan tal cual, sin recortar ni recolorear |
| `usuario/recursos/firmas/` | **Sólo lectura** | Imágenes de firma |
| `usuario/entregables/` | **Crear archivos nuevos** | Nunca editar ni borrar uno existente sin pedido explícito |

Prohibido en toda la zona del usuario, sin excepción:

1. Escribir, editar o crear archivos (salvo `usuario/entregables/`).
2. Renombrar o mover.
3. Borrar.
4. Completar valores `PENDIENTE`.
5. Versionar en git.

## Cómo se hace cumplir

La frontera no depende de la buena voluntad. Tiene tres mecanismos:

**1. Estructura.** La separación es física. `usuario/` no contiene ningún archivo
nuestro, salvo los `.gitkeep` que preservan las carpetas vacías en un clon.

**2. Git.** `.gitignore` excluye `usuario/**` completo. No hay reglas por subcarpeta
que puedan quedar desactualizadas: una zona, una regla. Si alguien intenta versionar
un archivo del usuario, aparece como ignorado.

**3. Verificación.**

```bash
python herramientas/scripts/verificar_limites.py
```

Comprueba que ningún archivo de `usuario/` esté versionado (salvo `.gitkeep`), que
ningún contrato `*.example` se haya filtrado a la zona del usuario y que la
estructura esperada exista. Código de salida `1` si algo se rompió.

## Cómo actualizamos las herramientas sin tocar el trabajo del usuario

| Herramienta | Garantía |
| --- | --- |
| `init_local.py` | Copia contratos a `usuario/datos/` **sólo si el archivo no existe**. Nunca sobrescribe. Se puede correr mil veces. |
| `validar_datos.py` | Sólo lee. No corrige ni completa nada. |
| `nuevo_entregable.py` | Resuelve una ruta libre. Si el nombre está ocupado agrega `-v2`. Nunca sobrescribe. |
| Contratos `*.example` | Viven en `herramientas/contratos/`. Actualizar el contrato no altera los datos reales del usuario. |

Consecuencia práctica: **podés actualizar el repositorio sin miedo**. Un `git pull`
nunca puede pisar un dato, una plantilla, un logo ni un entregable, porque ninguno
de esos archivos está versionado.

## Cómo agregar un dato nuevo

1. Se agrega la columna o clave al contrato en `herramientas/contratos/`.
2. El usuario actualiza su archivo real en `usuario/datos/`.
3. `validar_datos.py` reporta el archivo real desactualizado hasta que lo haga.

El orden importa: el contrato se versiona, el dato se completa localmente.

## Zona del usuario en detalle

```text
usuario/
├── datos/
│   ├── organizacion/
│   │   ├── entidad.csv        # datos legales, contacto, identidad visual
│   │   ├── contactos.csv      # directorio interno con roles
│   │   └── firmantes.csv      # quién firma y qué documentos
│   ├── tablas/
│   │   ├── servicios.csv      # catálogo con código único
│   │   ├── tarifas.csv        # precios y vigencia
│   │   └── horarios.csv       # programación de atención
│   └── entrada/               # insumos crudos
├── plantillas/
│   ├── propias/               # plantillas del usuario (ganan siempre)
│   └── oficiales/             # membretes y formatos de la organización
├── generadores/               # plantilla del usuario escrita en código (Python o JS)
├── recursos/
│   ├── logos/                 # logos e isotipos
│   └── firmas/                # imágenes de firma
└── entregables/
    ├── word/                  # .docx
    ├── pdf/                   # .pdf
    ├── excel/                 # .xlsx
    ├── markdown/              # .md
    └── borradores/            # versiones de trabajo
```

### Espacio de trabajo: usar la herramienta con los datos en otro lado

Por defecto la zona del usuario es `usuario/`, adentro del repositorio. Si
querés tener tus datos **fuera** —otro disco, otra carpeta, un cliente distinto
por carpeta— no copies el repositorio: apuntá la herramienta.

```bash
python herramientas/scripts/generar_documento.py --tipo manual --workspace D:\clientes\clinica-a
python herramientas/scripts/validar_datos.py --workspace D:\clientes\clinica-a
python herramientas/scripts/init_local.py --workspace D:\clientes\clinica-a
```

El **espacio de trabajo** es la carpeta que contiene `datos/`, `plantillas/`,
`generadores/`, `recursos/` y `entregables/`. La precedencia es fija:

```text
--workspace <ruta>                    ← gana siempre
ORQUESTADOR_WORKSPACE=<ruta>          ← variable de entorno
<repo>/usuario                        ← por defecto
```

Consecuencias:

- Podés atender varios clientes con la misma herramienta, un espacio por cliente.
- Actualizar el repositorio no toca tus datos, porque ni siquiera están adentro.
- Un espacio externo **no puede versionarse en git**: `verificar_limites.py` lo
  informa y sigue. La frontera se mantiene igual, sólo cambió de lugar.

### Precedencia de plantillas

Al generar un documento, el orden de búsqueda es fijo:

```text
usuario/generadores/<nombre>/             ← gana siempre: plantilla del usuario en código
usuario/plantillas/propias/<tipo>-*
usuario/plantillas/oficiales/<tipo>-*
membrete declarado en entidad.csv
formato por defecto del motor
```

El generador propio del usuario se ejecuta como subproceso y nunca se importa:
el motor no depende de ese código. El contrato está en
`herramientas/docs/contrato-generador.md`.

Se trabaja siempre sobre una **copia**. La plantilla original nunca se modifica.

### Convención de nombres de plantillas

```text
<tipo-de-documento>-<variante>.<ext>
```

Ejemplos: `propias/memorandum-interno.docx`, `oficiales/membrete-oficial.docx`,
`oficiales/hoja-membretada-a4.docx`. `<variante>` es opcional.

## Si el usuario quiere otra estructura

La estructura de `usuario/` es la que el agente espera, pero no está grabada en
piedra. Cambiarla implica tocar tres lugares: los contratos en
`herramientas/contratos/`, la constante de carpetas en `herramientas/scripts/init_local.py`
y las rutas de `herramientas/docs/`. Nada del contenido del usuario se pierde.
