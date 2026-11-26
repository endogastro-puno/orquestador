# Reglas del Proyecto Orquestador Documental

Manual operativo que el agente lee en cada sesión. Define de quién es cada carpeta,
cómo se produce un documento y qué no se hace nunca.

## Propósito

Generar documentos administrativos —Word (`.docx`), PDF, Markdown (`.md`) y Excel
(`.xlsx`)— a partir de una fuente de datos canónica, plantillas propias o oficiales, y
las skills instaladas.

Tres invariantes que no se negocian:

1. **`usuario/` es del usuario.** Nosotros no lo modificamos.
2. **Ningún dato del documento se inventa.** Sale de `usuario/datos/` o lo aporta el usuario.
3. **Ninguna salida queda fuera de `usuario/entregables/`.**

## Zona del usuario y zona de herramientas — REGLA NÚMERO UNO

El repositorio tiene dos zonas con dueños distintos. La frontera es física, no una
convención de estilo.

| Zona | Dueño | Nuestra relación |
| --- | --- | --- |
| `usuario/` | El usuario | **Sólo leer.** Nunca escribir, renombrar, mover ni borrar |
| `herramientas/`, `.opencode/`, `odd/`, `AGENTS.md`, `README.md` | Nosotros | Mantener y versionar |

> Nuestro trabajo termina en `herramientas/`.
> En `usuario/` sólo damos facilidades: carpetas creadas, contratos, validación y
> resolución de rutas. **El contenido lo produce el usuario.**

### Permisos exactos dentro de `usuario/`

| Ruta | Permiso | Detalle |
| --- | --- | --- |
| `usuario/datos/` | **Sólo lectura** | Los `PENDIENTE` los completa el usuario, no el agente |
| `usuario/datos/entrada/` | **Sólo lectura** | Insumos crudos: Excel, PDF, texto |
| `usuario/plantillas/propias/` | **Sólo lectura** | Precedencia máxima al generar |
| `usuario/plantillas/oficiales/` | **Sólo lectura** | Membretes y formatos de la organización |
| `usuario/generadores/` | **Sólo lectura y ejecución** | Plantilla del usuario escrita en código (Python o JS). Se ejecuta como subproceso; nunca se edita |
| `usuario/recursos/logos/` | **Sólo lectura** | Se insertan tal cual, sin recortar ni recolorear |
| `usuario/recursos/firmas/` | **Sólo lectura** | Imágenes de firma |
| `usuario/entregables/` | **Crear archivos nuevos** | Nunca editar ni borrar uno existente sin pedido explícito |
| `usuario/indice/` | **Regenerable** | Lo crea `indexar_documentos.py`; se puede borrar y reconstruir. Nunca se versiona |

Prohibido en toda la zona del usuario, sin excepción: escribir o crear archivos (salvo
`usuario/entregables/`), renombrar, mover, borrar, completar valores `PENDIENTE` y
versionar en git.

La frontera se verifica, no se asume:

```bash
python herramientas/scripts/verificar_limites.py
```

Detalle completo en `herramientas/docs/limites.md`.

### Espacio de trabajo (`--workspace`)

`usuario/` es el espacio de trabajo **por defecto**. Si los datos del usuario viven
en otra carpeta —otro cliente, otro disco—, todos los comandos aceptan
`--workspace <ruta>` o la variable `ORQUESTADOR_WORKSPACE`. Precedencia:
`--workspace` > `ORQUESTADOR_WORKSPACE` > `<repo>/usuario`.

```bash
python herramientas/scripts/generar_documento.py --tipo manual --workspace D:\clientes\clinica-a
python herramientas/scripts/validar_datos.py --workspace D:\clientes\clinica-a
python herramientas/scripts/init_local.py --workspace D:\clientes\clinica-a
```

Un espacio externo no puede versionarse en git; `verificar_limites.py` lo informa.
La regla de zona no cambia: sólo cambia la carpeta donde vive.

## Habilidades y herramientas

Catálogo único de lo que sabemos hacer: `herramientas/docs/habilidades.md`.
Si una habilidad no está ahí, no existe: se pregunta antes de inventarla.
Resumen operativo:

| Para… | Skill | Script |
| --- | --- | --- |
| Leer Word, PDF, Excel, CSV, texto, imágenes (también `.doc`/`.xls` viejos) | — | `leer_documento.py` |
| Leer un escaneado o foto | `pdf` | `ocr_documento.py` |
| Mapear carpetas / buscar en el mapa | — | `indexar_documentos.py` / `buscar_documentos.py` |
| Traer tu plantilla / crear una inicial | — | `instalar_plantilla.py` / `nueva_plantilla.py` |
| Redactar administrativo / documento largo | `internal-comms` / `doc-coauthoring` | — |
| Generar `.docx` / planilla / PDF | `docx` / `xlsx` / `pdf` | `generar_documento.py` |
| Todo desde un menú | — | `menu.py` |

## Mapa del repositorio

| Ruta | Qué es | Dueño |
| --- | --- | --- |
| `usuario/datos/` | Fuente de datos real del usuario | usuario |
| `usuario/plantillas/propias/` | Plantillas del usuario (máxima precedencia) | usuario |
| `usuario/plantillas/oficiales/` | Membretes y formatos de la organización | usuario |
| `usuario/generadores/` | Plantilla del usuario escrita en código (Python o JS) | usuario |
| `usuario/recursos/logos/` · `firmas/` | Identidad visual y firmas | usuario |
| `usuario/entregables/word/` `pdf/` `excel/` `markdown/` `borradores/` | Salidas | usuario |
| `usuario/indice/` | Mapa de las carpetas indexadas; regenerable | usuario |
| `herramientas/contratos/` | Contratos `*.example` de la fuente de datos | nosotros |
| `herramientas/scripts/` | Inicialización, validación, rutas y verificación de límites | nosotros |
| `herramientas/tests/` | Pruebas de regresión (sólo biblioteca estándar) | nosotros |
| `herramientas/docs/` | Catálogo de tipos, flujo, límites de zona y lectura de documentos | nosotros |
| `herramientas/ejemplos/` | Ejemplo de generador propio del usuario | nosotros |
| `EMPEZAR.bat` · `MENU.bat` | Atajos de doble clic para Windows: primer arranque y menú | nosotros |
| `INSTALACION.md` | Qué instalar para que el repositorio funcione | nosotros |
| `.opencode/skills/` | Skills instaladas | nosotros |
| `odd/` | Registro de decisiones de desarrollo | nosotros |

Nada de `usuario/` está versionado, salvo los `.gitkeep` que preservan la estructura.

## Flujo obligatorio

Detalle completo en `herramientas/docs/flujo-de-trabajo.md`. Resumen:

1. **Identificar el tipo** en `herramientas/docs/tipos-de-documento.md` y el formato
   destino (`.md`, `.docx`, `.xlsx`, `.pdf`). Si el pedido es ambiguo, proponer el tipo
   más cercano y confirmar antes de generar.
2. **Validar la fuente**: `python herramientas/scripts/validar_datos.py`. Si hay
   errores, no se redacta; se informa qué falta. Si hay `PENDIENTE` en campos que el
   documento usa, se pregunta por esos campos y se detiene.
   Si el pedido trae insumos (Word, PDF, Excel) en `usuario/datos/entrada/`, se leen
   con `python herramientas/scripts/leer_documento.py <archivo> --json`. Un insumo que
   no se leyó no se usa: no se resume de memoria. Si el insumo es un PDF escaneado
   (aviso + código 2) o una foto, se lee con
   `python herramientas/scripts/ocr_documento.py <archivo> --json` (cadena OCR en
   `herramientas/docs/ocr-de-documentos.md`).
   Si el usuario no sabe dónde está un archivo, se busca en el índice con
   `python herramientas/scripts/buscar_documentos.py "<texto>" --json`; si la raíz
   aún no está mapeada, primero
   `python herramientas/scripts/indexar_documentos.py --ruta <carpeta>`.
3. **Resolver la plantilla** con la precedencia de la sección siguiente. Si el
   usuario trae su propia plantilla en cualquier ruta de su máquina, se copia con
   `python herramientas/scripts/instalar_plantilla.py --origen <ruta> --tipo <tipo>`:
   nunca se pega a mano en `usuario/plantillas/`.
4. **Redactar** con el esqueleto del tipo y con `internal-comms` o `doc-coauthoring`.
5. **Generar** con la skill correspondiente sobre la ruta que devuelve
   `python herramientas/scripts/nuevo_entregable.py`.
6. **Verificar** con la checklist de la sección «Verificación antes de entregar».
7. **Entregar** informando ruta, tipo, datos usados y pendientes.

## Fuente de datos — regla anti-invención

La verdad está en `usuario/datos/`. Los contratos están en `herramientas/contratos/`
(ver su `README.md`).

| Archivo real | Contenido |
| --- | --- |
| `usuario/datos/organizacion/entidad.csv` | Razón social, RUC, domicilio, contacto, colores, rutas de logo y membrete |
| `usuario/datos/organizacion/contactos.csv` | Directorio interno con roles: destinatario, copia, aprobador, firmante |
| `usuario/datos/organizacion/firmantes.csv` | Quién firma y qué tipos de documento puede firmar |
| `usuario/datos/tablas/servicios.csv` | Catálogo de servicios con código único |
| `usuario/datos/tablas/tarifas.csv` | Precios por servicio y vigencia |
| `usuario/datos/tablas/horarios.csv` | Programación de atención |
| `usuario/datos/tablas/actividades.csv` | Metas y actividades del plan operativo |
| `usuario/datos/tablas/partidas.csv` | Partidas presupuestarias con montos y periodo |
| `usuario/datos/organizacion/puestos.csv` | Puestos y funciones para el tipo `manual` |

Reglas:

- Un dato que no está en `usuario/datos/` **no existe**. Se pregunta.
- Un campo con `PENDIENTE` **no está confirmado**. Se pregunta.
- El agente **no completa los `PENDIENTE`**, ni siquiera con el valor que parece
  correcto: ese archivo es la voz del usuario. Se pide el dato y lo escribe él.
- Nunca se completa un faltante con un valor «típico», un ejemplo plausible ni un
  marcador de posición silencioso. Un RUC, un precio o un nombre inventado en un
  documento oficial es un daño real.
- Toda cifra del documento debe poder rastrearse a `usuario/datos/tablas/`.
- Si el usuario dicta un dato en el chat, ese dato manda para ese documento y se le
  sugiere agregarlo a `usuario/datos/` para no volver a preguntarlo.

## Plantillas — precedencia

Orden fijo, sin excepciones:

1. `usuario/generadores/<nombre>/` — la plantilla del usuario escrita en código
   (Python o JS). **Gana siempre.** Es código suyo: el motor lo ejecuta como
   subproceso, nunca lo importa y nunca lo modifica. Contrato en
   `herramientas/docs/contrato-generador.md`.
2. `usuario/plantillas/propias/<tipo>-*` — la plantilla propia del usuario.
3. `usuario/plantillas/oficiales/<tipo>-*` — formato oficial del tipo.
4. Membretes declarados en `entidad.csv` (`membrete_word`, `membrete_excel`).
5. Formato por defecto: sobrio, corporativo, sin sobrecarga visual.

Se trabaja sobre una **copia**. La plantilla original nunca se modifica. Convención de
nombres: `<tipo-de-documento>-<variante>.<ext>`.

Cuando hay generador propio, el motor sigue siendo dueño del **contenido** (resuelve
placeholders, valida `PENDIENTE`, expande tablas) y el generador aplica el **formato**.

## Tipos de documento

Catálogo completo con datos obligatorios y esqueletos de secciones en
`herramientas/docs/tipos-de-documento.md`. Tipos soportados: `memorandum`, `circular`,
`informe`, `manual`, `plan-operativo`, `oficio`, `solicitud`, `constancia`, `acta`,
`reporte`, `cotizacion`, `comunicado`.

Los tipos `manual` y `plan-operativo` son **declarativos**: su estructura vive en
`herramientas/contratos/tipos/<tipo>.json` y se producen con
`python herramientas/scripts/generar_documento.py --tipo <tipo>`. Para agregar un tipo
nuevo se escribe un spec y, si trae datos nuevos, un contrato `.example`. **No se escribe
un generador nuevo ni se pegan datos de empresa en el código.**

Skills por formato:

| Formato | Skill |
| --- | --- |
| `.docx` | `docx` |
| `.pdf` | `pdf` |
| `.xlsx` | `xlsx` |
| `.md` | escritura directa |
| Contenido administrativo | `internal-comms` |
| Documento largo iterativo | `doc-coauthoring` |
| Identidad visual | `brand-guidelines` |

Los scripts que generan `.docx` con la librería npm `docx` deben ejecutarse **desde el
repositorio**: Node resuelve `node_modules/` desde la carpeta del script. Un script en un
temporal falla con `Cannot find module 'docx'`. Si hace falta uno fuera, se define
`NODE_PATH` apuntando a `node_modules`. Detalle en `INSTALACION.md`.

## Convención de nombres

```text
usuario/entregables/<carpeta>/AAAA-MM-DD_slug.ext
```

Sin espacios, sin tildes, sin mayúsculas; se separa con guiones. No se calcula a mano:

```bash
python herramientas/scripts/nuevo_entregable.py --tipo word --nombre "Memorándum de horarios"
# usuario/entregables/word/2026-11-25_memorandum-de-horarios.docx
```

Colisión de nombres: agrega `-v2`, `-v3`, etc. **Nunca sobrescribe.**

## Verificación antes de entregar

| # | Control |
| --- | --- |
| 1 | El archivo existe, abre y no está vacío |
| 2 | Está dentro de `usuario/entregables/<tipo>/` con el nombre correcto |
| 3 | No quedan marcadores: `PENDIENTE`, `<correlativo>`, `TODO`, `XXX` |
| 4 | Las cifras cierran con `usuario/datos/tablas/` |
| 5 | Nombres y cargos coinciden con `contactos.csv` / `firmantes.csv` |
| 6 | El formato es el pedido |
| 7 | Logo y membrete son los declarados en `entidad.csv` |

Si falla un control, se corrige antes de entregar. Los controles 3 a 5 son los que
atrapan errores reales.

Cerrá cada cambio de código con su línea de riesgo (`Risk: ...`) cuando corresponda.

## Scripts

| Script | Uso |
| --- | --- |
| `herramientas/scripts/empezar.py` | Primer arranque completo: verifica entorno, instala si se pide, crea carpetas, copia contratos y deja una plantilla base por tipo. `--plan` no escribe |
| `herramientas/scripts/init_local.py` | Sólo estructura: crea carpetas del usuario y copia contratos a datos reales |
| `herramientas/scripts/validar_datos.py` | Valida `usuario/datos/`; `--estricto` falla si queda algún `PENDIENTE` |
| `herramientas/scripts/nuevo_entregable.py` | Resuelve la ruta del entregable; `--selftest` verifica la lógica |
| `herramientas/scripts/verificar_limites.py` | Comprueba que nada de `usuario/` esté versionado |
| `herramientas/scripts/verificar_entorno.py` | Comprueba que el entorno tenga instalado lo que cada formato necesita |
| `herramientas/scripts/instalar_todo.py` | Instala lo que falte: `--plan` muestra, `--si` ejecuta. Windows |
| `herramientas/scripts/generar_documento.py` | Genera un documento desde `herramientas/contratos/tipos/<tipo>.json` y los CSV |
| `herramientas/scripts/listar_generadores.py` | Lista los generadores propios del usuario en `usuario/generadores/` |
| `herramientas/scripts/leer_documento.py` | Lee `.docx`, `.doc`, `.pdf`, `.xlsx`, `.xls`, `.csv`, `.md`, `.txt` e imágenes con OCR; los formatos viejos se convierten con LibreOffice a un temporal; devuelve texto y estructura |
| `herramientas/scripts/menu.py` | Menú interactivo que lista y corre todas las facilidades; `--opcion N` para uso directo |
| `herramientas/scripts/instalar_plantilla.py` | Copia una plantilla existente del usuario a `plantillas/propias/` con el nombre canónico |
| `herramientas/scripts/nueva_plantilla.py` | Crea una plantilla inicial sobria (`.docx`, `.xlsx` o `.md`) para un tipo |
| `herramientas/scripts/indexar_documentos.py` | Mapea una carpeta completa y guarda el índice incremental en `usuario/indice/`; `--con-ocr` reintenta escaneados con Tesseract |
| `herramientas/scripts/buscar_documentos.py` | Busca en el índice por nombre y contenido, con filtros (`--tipo`, `--escaneados`); también mira el `texto_ocr` |
| `herramientas/scripts/ocr_documento.py` | Lee un PDF escaneado o foto con OCR; `--salida` guarda la transcripción en `entregables/` |
| `herramientas/scripts/selftest.py` | Prueba de humo del motor en un temporal; no toca `usuario/` |

Detalle y reglas para scripts nuevos en `herramientas/scripts/README.md`.
Qué instalar en la máquina: `INSTALACION.md`.

Pruebas de regresión (sólo biblioteca estándar, sin `pytest`):

```bash
python -m unittest discover -s herramientas/tests -v
```

Si el usuario dice que no puede instalar o que no entiende la terminal, la
respuesta es `python herramientas/scripts/empezar.py`: un solo comando que
revisa qué falta, pregunta si lo instala y deja todo preparado. La guía tiene
una sección «Instalación sin vueltas» pensada para usuarios no técnicos: no la
reemplaces por una lista de comandos sueltos.

## Versionado y privacidad

Este repositorio es público. Sólo se versiona material reutilizable.

**Se versiona:** `.opencode/skills/**`, `herramientas/**`, `odd/**`, `AGENTS.md`,
`README.md`, `INSTALACION.md`, `.gitignore`, `.gitattributes`, `requirements.txt`,
`package.json`, `package-lock.json`, `LICENSE` y los `.gitkeep` que preservan la
estructura de `usuario/`.

**Nunca se versiona:** nada de `usuario/` (salvo `.gitkeep`) ni `.atl/**`.

Reglas:

1. Nunca `git add -f` sobre rutas de `usuario/`.
2. Nunca pegar datos personales en archivos versionados: pacientes, historias
   clínicas, DNI, RUC reales, correos, teléfonos ni resultados de estudios.
3. Antes de un commit: `python herramientas/scripts/verificar_limites.py` y
   `git status --short`.
4. Los scripts versionados deben ser genéricos: sin rutas absolutas de la máquina y
   sin datos incrustados.
5. Compartir una plantilla, un logo o un dato del usuario requiere autorización
   explícita del responsable.
6. Flujo de git: se trabaja **directo en `main`**, sin ramas ni PR intermedios, salvo
   pedido explícito del usuario. Commits convencionales en español, sin atribución
   de IA. Push a `origin/main` al cierre de cada unidad de trabajo.

## Prohibiciones

- Modificar, renombrar, mover o borrar cualquier cosa dentro de `usuario/`, salvo crear
  entregables nuevos en `usuario/entregables/`.
- Modificar el código de `usuario/generadores/`: es del usuario. Se ejecuta, se lee y
  se depura desde afuera; si falla, se le muestra el error y se propone el arreglo,
  pero no se edita su archivo.
- Completar los `PENDIENTE` de `usuario/datos/`: eso lo hace el usuario.
- Inventar, estimar o «completar» datos que la fuente no tiene.
- Guardar un documento fuera de `usuario/entregables/` o dejar archivos sueltos en la raíz.
- Modificar una plantilla original en lugar de trabajar sobre una copia.
- Sobrescribir un entregable existente.
- Entregar un documento con `PENDIENTE` o `<correlativo>` en el cuerpo.
- Entregar `.csv` cuando se pidió Excel (`.xlsx`).
- Crear carpetas nuevas en la raíz sin justificarlo: la estructura ya está definida.
