# Orquestador Documental — EndoGastro Puno

[![CI](https://github.com/endogastro-puno/orquestador/actions/workflows/ci.yml/badge.svg)](https://github.com/endogastro-puno/orquestador/actions/workflows/ci.yml)

Repositorio de trabajo para generar documentos administrativos con OpenCode:
**Word**, **PDF**, **Markdown** y **Excel**, a partir de una fuente de datos canónica y
de plantillas propias o oficiales.

## Dos zonas, dos dueños

```text
orquestador/
├── usuario/          ← TUYO. Tus datos, tus plantillas, tus logos, tus documentos.
│                       Nunca lo modificamos. Nunca se sube a git.
└── herramientas/     ← NUESTRO. Scripts, contratos y documentación.
                        Se versiona y se actualiza sin tocar tu trabajo.
```

> **Nuestro trabajo termina en `herramientas/`.**
> En `usuario/` sólo damos facilidades: las carpetas creadas, los contratos, la
> validación y la resolución de rutas. **El contenido lo producís vos.**

| Zona | Qué contiene | ¿Se sube a git? | ¿Lo tocamos? |
| --- | --- | --- | --- |
| `usuario/` | Datos, plantillas, recursos, entregables | **No** (sólo los `.gitkeep` de estructura) | **Nunca** |
| `herramientas/` | Contratos, scripts, documentación | Sí | Sí |
| `.opencode/skills/` | Skills instaladas | Sí | Sí |
| `odd/` | Registro de decisiones de desarrollo | Sí | Sí |

Reglas de la frontera:

- `usuario/datos/`, `usuario/plantillas/`, `usuario/recursos/` → **sólo lectura**.
- `usuario/generadores/` → **sólo lectura y ejecución**: es tu plantilla escrita en
  código. El motor la corre; no la modifica.
- `usuario/entregables/` → se crean archivos **nuevos**; nunca se sobrescribe ni se borra.
- Los valores `PENDIENTE` los completa el usuario. El agente pregunta, no rellena.

Verificación de que la frontera se respeta:

```bash
python herramientas/scripts/verificar_limites.py
```

Detalle completo en [`herramientas/docs/limites.md`](herramientas/docs/limites.md).

## La idea en una línea

> El agente no inventa: lee `usuario/datos/`, aplica la plantilla y escribe en `usuario/entregables/`.

## Todo desde un menú

Sin memorizar comandos:

```bash
python herramientas/scripts/menu.py
```

Lista las facilidades y corre la que elijas: preparar tus datos, validarlos,
leer un insumo, traer tu plantilla, crear una plantilla inicial, generar un
documento o revisar el entorno. Cada opción corre otro script del repositorio
y pasa su código de salida tal cual. También directo, sin menú:

```bash
python herramientas/scripts/menu.py --opcion 5 -- entrada.docx --json
```

## Leer insumos: Word, PDF, Excel, texto e imágenes

```bash
python herramientas/scripts/leer_documento.py usuario/datos/entrada/informe.docx --json
python herramientas/scripts/leer_documento.py expediente-viejo.doc --texto
python herramientas/scripts/leer_documento.py escaneo.png --texto
```

`.docx`, `.csv`, `.md` y `.txt` no necesitan nada instalado. `.pdf` y `.xlsx`
usan las dependencias de `requirements.txt`. Los **formatos viejos** (`.doc`,
`.xls`, `.rtf`, `.odt`, `.ods`) se convierten a un temporal con LibreOffice y se
leen de ahí: el original no se toca. Las imágenes (`.png`, `.jpg`, `.tif`,
`.bmp`, `.webp`) se leen con OCR opcional — si falta, el error dice qué
instalar. Detalle del contrato de salida:
[`herramientas/docs/lectura-de-documentos.md`](herramientas/docs/lectura-de-documentos.md).

## El mapa de tus documentos

Tus carpetas pueden ser una selva — `FOLDER-PRINCIPAL` con subcarpetas por todos
lados. No hace falta recorrerlas a pie cada vez: se mapean **una vez** y después
se busca en el mapa, en milisegundos:

```bash
python herramientas/scripts/indexar_documentos.py --ruta D:\FOLDER-PRINCIPAL
python herramientas/scripts/buscar_documentos.py "cotización de mantenimiento"
python herramientas/scripts/buscar_documentos.py --escaneados
```

La primera pasada lee cada Word y PDF y guarda el índice en `indice/` (tu zona,
nunca en git). El índice es **incremental**: volver a correrla sólo relee lo que
cambió. La búsqueda encuentra por nombre **y por el texto de adentro**, sin
tildes ni mayúsculas. Y los **PDF escaneados quedan marcados**: saber dónde están
todos los que necesitan OCR es una sola consulta.

Si además querés que esos escaneados sean buscables por contenido, mapeá con OCR:

```bash
python herramientas/scripts/indexar_documentos.py --ruta D:\FOLDER-PRINCIPAL --con-ocr
python herramientas/scripts/ocr_documento.py expediente-escaneado.pdf --texto
```

Necesita Tesseract (se instala con `instalar_todo.py --si --con-ocr`). Detalle:
[`herramientas/docs/ocr-de-documentos.md`](herramientas/docs/ocr-de-documentos.md).

## Qué sabemos hacer (habilidades)

El catálogo completo —leer, plantillas, redactar, generar, entorno— con su
skill y su script cada una:
[`herramientas/docs/habilidades.md`](herramientas/docs/habilidades.md).
Si algo no está ahí, no existe: preguntá antes de suponerlo.

## Tu plantilla, la que ya tenés

No hace falta rediseñar nada: si ya tenés un membrete o una planilla que usás
hace años, se instala con un comando y queda en el lugar donde el orquestador
la busca primero:

```bash
python herramientas/scripts/instalar_plantilla.py --origen "C:\Users\vo\Documentos\membrete.docx" --tipo oficio --variante Corporativa
```

Se **copia**, no se mueve: tu original queda donde está. Nunca sobrescribe: si
ya existe una plantilla con ese nombre, te lo dice y no toca nada. Y si no
tenés ninguna todavía:

```bash
python herramientas/scripts/nueva_plantilla.py --tipo informe
```

crea una base sobria con los marcadores `{{titulo}}` `{{fecha}}` `{{cuerpo}}`;
el estilo lo ponés vos.

## Tus datos, donde vos quieras

`usuario/` es sólo el espacio de trabajo **por defecto**. Si preferís tener tus datos
en otra carpeta —otro disco, una carpeta sincronizada, un cliente por carpeta— no
hace falta copiar el repositorio:

```bash
python herramientas/scripts/init_local.py --workspace D:\clientes\clinica-a
python herramientas/scripts/generar_documento.py --tipo manual --workspace D:\clientes\clinica-a
```

También sirve la variable de entorno `ORQUESTADOR_WORKSPACE`. Precedencia:
`--workspace` → variable de entorno → `usuario/`.

Un espacio externo no se versiona en git; la frontera se mantiene igual, sólo cambia
de lugar. Detalle en [`herramientas/docs/limites.md`](herramientas/docs/limites.md).

## Tu plantilla, escrita en código

Si querés que **todos** tus documentos salgan con tu propia plantilla, podés
escribirla como código —Python o JavaScript— y dejarla en tu zona:

```text
usuario/generadores/corporativo/
  generador.json    # qué tipos cubre y cómo se ejecuta
  generador.py      # tu código
```

```bash
python herramientas/scripts/listar_generadores.py
python herramientas/scripts/generar_documento.py --tipo manual
```

El motor sigue siendo dueño del contenido (resuelve los datos y valida que no
queden `PENDIENTE`); tu código aplica el formato: membrete, tipografía, color,
sellos y firmas.

Es **tu** código: nunca se sube a git, nunca lo modificamos y nunca lo
importamos — lo ejecutamos como proceso aparte, así que un error tuyo no rompe
el motor. Contrato completo:
[`herramientas/docs/contrato-generador.md`](herramientas/docs/contrato-generador.md).

## Requisitos

- [OpenCode](https://opencode.ai) — el agente lee `AGENTS.md` al iniciar cada sesión.
- Python 3.10+ y git.
- Dependencias de generación documental: Python (pip), Node.js (npm), Pandoc,
  LibreOffice y Poppler.

> **¿No querés complicarte?** Hay una sección pensada para eso en
> [`INSTALACION.md`](INSTALACION.md#instalación-sin-vueltas): un solo comando,
> sin decisiones. El resto de la guía es el detalle técnico.

Comprobación en un comando:

```bash
python herramientas/scripts/verificar_entorno.py
```

Dice qué falta, para qué formato hace falta y cómo se instala. Y si preferís que
lo resuelva solo:

```bash
python herramientas/scripts/instalar_todo.py
```

Los scripts de `herramientas/scripts/` funcionan **sin instalar nada**: usan sólo la
biblioteca estándar.

## Puesta en marcha

Un solo comando deja la PC lista — estructura, datos base y una plantilla por tipo:

```bash
python herramientas/scripts/empezar.py
```

Revisa el entorno, ofrece instalar lo que falta, crea tus carpetas, copia los datos base
y deja las **12 plantillas iniciales** (una por tipo). Nunca pisa nada: si ya tenés un
dato o una plantilla de ese tipo, la respeta. Antes de escribir podés ver el plan:

```bash
python herramientas/scripts/empezar.py --plan           # qué haría, sin tocar nada
python herramientas/scripts/empezar.py --si             # sin preguntar
python herramientas/scripts/empezar.py --sin-plantillas # sólo carpetas y datos
```

Después completás cada `PENDIENTE` de tus datos y validás:

```bash
python herramientas/scripts/validar_datos.py  # confirma que la fuente quedó consistente
```

`empezar.py` copia cada contrato de `herramientas/contratos/` a tu archivo real en
`usuario/datos/`. **Sólo si el archivo no existe**: nunca sobrescribe lo que ya tenés.
Los `PENDIENTE` los completás vos: el agente no inventa datos.

## Estructura

```text
orquestador/
├── AGENTS.md                       # manual operativo del agente
├── README.md
├── INSTALACION.md                  # qué instalar para que todo funcione
├── requirements.txt                # dependencias pip
├── package.json                    # dependencia npm `docx`
├── .opencode/skills/               # docx, pdf, xlsx, internal-comms, doc-coauthoring, ...
├── odd/                            # decisiones de desarrollo
│
├── usuario/                        # ← TU ZONA
│   ├── datos/
│   │   ├── organizacion/           # entidad.csv, contactos.csv, firmantes.csv
│   │   ├── tablas/                 # servicios.csv, tarifas.csv, horarios.csv
│   │   └── entrada/                # insumos crudos (Excel, PDF, texto)
│   ├── plantillas/
│   │   ├── propias/                # tus plantillas (ganan siempre)
│   │   └── oficiales/              # membretes y formatos de la organización
│   ├── generadores/                # tu plantilla escrita en código (Python o JS)
│   ├── recursos/
│   │   ├── logos/                  # logos e isotipos
│   │   └── firmas/                 # imágenes de firma
│   └── entregables/
│       ├── word/  pdf/  excel/  markdown/  borradores/
│
└── herramientas/                   # ← NUESTRA ZONA
    ├── contratos/                  # *.example: el esquema de tus datos
    ├── docs/
    │   ├── habilidades.md            # qué sabemos hacer: skill + script de cada cosa
    │   ├── limites.md              # la frontera, en detalle
    │   ├── tipos-de-documento.md   # 12 tipos con datos obligatorios y esqueletos
    │   ├── flujo-de-trabajo.md     # pipeline de 7 pasos
    │   ├── lectura-de-documentos.md # leer Word, PDF, Excel, texto e imágenes
    │   ├── ocr-de-documentos.md    # leer escaneados con Tesseract
    │   └── contrato-generador.md   # cómo se usa tu plantilla escrita en código
    ├── ejemplos/                   # ejemplo de generador propio
    └── scripts/
        ├── menu.py                 # todas las facilidades, sin memorizar comandos
        ├── empezar.py              # primer arranque: entorno + estructura + datos + plantillas
        ├── init_local.py           # crea tu estructura y tus datos
        ├── validar_datos.py        # valida tus datos contra los contratos
        ├── nuevo_entregable.py     # resuelve la ruta con la convención de nombres
        ├── verificar_limites.py    # comprueba que la frontera se respete
        ├── leer_documento.py       # lee Word, PDF, Excel, CSV, texto e imágenes (OCR)
        ├── ocr_documento.py        # lee escaneados y fotos con Tesseract
        ├── instalar_plantilla.py   # trae tu plantilla existente a plantillas/propias/
        ├── nueva_plantilla.py      # crea una plantilla inicial sobria
        ├── indexar_documentos.py   # mapea una carpeta completa (índice incremental)
        ├── buscar_documentos.py    # busca en el índice: nombres y contenido
        ├── listar_generadores.py   # lista tu plantilla en código, si tenés una
        ├── selftest.py             # prueba de humo: ¿el motor funciona acá?
        └── verificar_entorno.py    # comprueba que el entorno tenga todo instalado
```

## Flujo de trabajo

1. Identificar el tipo de documento (`herramientas/docs/tipos-de-documento.md`).
2. Validar la fuente: `python herramientas/scripts/validar_datos.py`.
3. Resolver la plantilla: tu generador en `usuario/generadores/` → `propias/` →
   `oficiales/` → membrete → formato por defecto.
4. Redactar con `internal-comms` o `doc-coauthoring`.
5. Generar con `docx`, `xlsx`, `pdf` o escritura directa para `.md`.
6. Verificar con la checklist de `AGENTS.md`.
7. Entregar informando ruta, datos usados y pendientes.

## Ejemplo de uso

> "Redactá un memorándum de actualización de horarios y exportalo a Word."

El agente valida `usuario/datos/`, detecta que es un `memorandum`, busca
`usuario/plantillas/propias/memorandum-*`, redacta con el esqueleto del catálogo,
resuelve la ruta

```text
usuario/entregables/word/2026-11-25_memorandum-de-horarios.docx
```

y genera el `.docx` con el membrete declarado en `entidad.csv`.

Si `usuario/datos/tablas/horarios.csv` está vacío o con `PENDIENTE`, **no redacta**:
pide los horarios primero.

## Convención de nombres

```text
usuario/entregables/<carpeta>/AAAA-MM-DD_slug.ext
```

Sin espacios, sin tildes, sin mayúsculas. No se calcula a mano:

```bash
python herramientas/scripts/nuevo_entregable.py --tipo word --nombre "Memorándum de horarios"
python herramientas/scripts/nuevo_entregable.py --tipo excel --nombre "Tarifas 2026" --json
```

Devuelve la ruta libre y resuelve colisiones con `-v2`, `-v3`. Nunca sobrescribe.

## Actualizar el repositorio sin perder tu trabajo

Un `git pull` **no puede** pisar un dato, una plantilla, un logo ni un entregable,
porque ninguno de esos archivos está versionado. La zona `usuario/` es invisible para
git salvo los `.gitkeep` de estructura.

Si una actualización agrega un campo nuevo al contrato, `validar_datos.py` te avisa
qué archivo tuyo quedó desactualizado. Vos decidís cuándo completarlo.

## Checklist antes de cada commit

```bash
python herramientas/scripts/verificar_limites.py
git status --short
```

No debe aparecer ninguna ruta de `usuario/` (salvo `.gitkeep`) ni `.atl/`. Si algo se
coló:

```bash
git rm -r --cached usuario
```

## Licencia

MIT — ver `LICENSE`.
