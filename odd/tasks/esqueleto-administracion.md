# Esqueleto administrativo del orquestador documental

Objetivo: convertir el repo en un sistema de generación de documentos administrativos
(Word, PDF, Markdown, Excel) con fuente de datos canónica, plantillas del usuario y
contratos versionados.
Rama: `main`. Entrega: trabajo local, sin push. Runner: `python` (scripts con `--selftest`).

## Specs

- **S1** — El repo debe producir documentos Word (`.docx`), PDF, Markdown (`.md`) y
  Excel (`.xlsx`) para administración, con `usuario/entregables/markdown/` como destino
  del Markdown.
- **S2** — Debe existir una fuente de datos canónica en `usuario/datos/` con: entidad
  legal y administrativa, contactos internos, firmantes, servicios, tarifas y horarios.
- **S3** — La fuente de datos se versiona sólo como contrato `*.example` en
  `herramientas/contratos/`; los archivos reales son privados y quedan fuera de git.
- **S4** — Regla anti-invención: un dato ausente o con `PENDIENTE` no se completa con
  supuestos; el agente pregunta y se detiene.
- **S5** — Plantillas propias del usuario soportadas con precedencia sobre las
  oficiales: `usuario/plantillas/propias/` → `usuario/plantillas/oficiales/` → membrete
  de `entidad.csv` → formato por defecto.
- **S6** — Esqueleto operativo documentado en `AGENTS.md`,
  `herramientas/docs/tipos-de-documento.md` y `herramientas/docs/flujo-de-trabajo.md`.
- **S7** — Scripts reutilizables sin dependencias externas: inicialización de la
  estructura local, validación de la fuente de datos y resolución de nombres de
  entregables.
- **S8** — Ningún archivo privado (entregables, datos reales, plantillas, logos,
  firmas, `.atl/`) puede quedar versionado; se verifica con `git add -A -n`.
- **S9** — Debe quedar inequívoco qué carpetas son del usuario y su trabajo, y que
  nosotros nunca las modificamos. Frontera física: `usuario/` (del usuario, fuera de
  git) y `herramientas/` (nuestras, versionadas). Sólo se lee de `usuario/`; se escribe
  únicamente en `usuario/entregables/`.
- **S10** — La frontera debe ser verificable por comando, no sólo declarativa:
  `verificar_limites.py` falla si algo de `usuario/` se versiona.
- **S11** — El agente no completa los `PENDIENTE` de `usuario/datos/`: los completa el
  usuario. El agente pide el dato.
- **S12** — Debe existir una guía de instalación separada (`INSTALACION.md`), referenciada
  desde `README.md`, que cubra **todo** lo necesario para que el repositorio funcione:
  programas del sistema, dependencias Python, dependencia Node, verificación y puesta en
  marcha. Nada de lo que la guía mande instalar puede ser innecesario, y nada necesario
  puede faltar.
- **S13** — La instalación debe ser comprobable por comando, no sólo legible:
  `herramientas/scripts/verificar_entorno.py` informa qué falta, para qué formato hace
  falta y cómo se instala. Sólo biblioteca estándar. Código de salida `1` si falta algo
  obligatorio.
- **S14** — `requirements.txt` debe declarar las dependencias **reales** de las skills
  instaladas, sin paquetes que ninguna skill use y sin opcionales: lo que es comodidad
  o sólo sirve para una tarea puntual (OCR, vistazo de una hoja) se documenta aparte y
  no se instala por defecto.
- **S15** — La guía debe tener una sección dedicada a usuarios **no técnicos** que
  quieren que funcione rápido y sin pensar: un solo comando, sin decisiones. Qué
  programa de oficina use el usuario (Word o LibreOffice) es indiferente y no debe
  plantearse como elección. El camino tiene que ser ejecutable por alguien que no sabe
  qué es un PATH: pasos numerados, qué escribir, qué esperar, cómo saber que terminó y
  qué hacer si falla.
- **S16** — La instalación no puede romper un entorno que ya funciona. Si Node.js lo
  administra NVM, el instalador no lo toca; si una librería ya está presente, no se
  reemplaza ni se degrada. Un ensayo en seco (`pip install --dry-run`) no puede mostrar
  ninguna desinstalación.

## Tasks

| ID | Spec | Ruta | Estado | Evidencia |
| --- | --- | --- | --- | --- |
| T1 | S2, S3 | `.gitignore` + contratos `datos/**/*.example` | hecho | `git add -A -n` lista sólo `*.example` |
| T2 | S1, S8 | `entregables/markdown/` + `.gitkeep` en carpetas privadas | hecho | 32 archivos reutilizables, 0 privados |
| T3 | S5 | `plantillas/README.md` + `plantillas/usuario/` y `corporativas/` | hecho | precedencia documentada |
| T4 | S6 | `AGENTS.md`, `docs/tipos-de-documento.md`, `docs/flujo-de-trabajo.md` | hecho | 10 tipos con datos obligatorios |
| T5 | S7 | `scripts/init_local.py` | hecho | crea 6 archivos de datos, exit 0 |
| T6 | S7 | `scripts/validar_datos.py` | hecho | detecta archivo faltante, columnas, integridad y fechas; exit 1 |
| T7 | S7 | `scripts/nuevo_entregable.py` | hecho | `--selftest` OK; colisión `-v2` OK |
| T8 | S9 | `usuario/` + `herramientas/` como zonas separadas | hecho | `git add -A -n` = 31 archivos, 0 de `usuario/` |
| T9 | S9 | `herramientas/contratos/` desacopla contrato de dato | hecho | ruta real derivada por convención, sin manifiesto |
| T10 | S10 | `herramientas/scripts/verificar_limites.py` | hecho | detecta archivo versionado y `*.example` colado; exit 1 |
| T11 | S9, S10 | `herramientas/docs/limites.md` | hecho | permisos por carpeta y mecanismos de cumplimiento |
| T12 | S14 | `requirements.txt` corregido | hecho | `python-docx` fuera (ninguna skill lo importa); 11 paquetes reales |
| T13 | S13 | `herramientas/scripts/verificar_entorno.py` | hecho | detecta 13 faltantes reales; `--formato` y `--strict` con exit codes probados |
| T14 | S12 | `INSTALACION.md` + `package.json` | hecho | IDs de `winget` verificados; `npm install` y generación `.docx` probados |
| T15 | S15 | `INSTALACION.md` § «Instalación sin vueltas» | hecho | 4 pasos, un comando, tabla de «lo que ves / qué hacés» |
| T16 | S15 | `herramientas/scripts/instalar_todo.py` | hecho | `--plan` exit 0; cancela sin instalar; fallo de `winget` reportado sin traza |
| T17 | S16 | `instalar_todo.py` + `verificar_entorno.py` + `requirements.txt` | hecho | guarda NVM verificada; `markitdown` y `pytesseract` a opcionales; dry-run sin desinstalaciones; 14 pruebas OK |

## Log

**L1** — Pedido original (verbatim):

> OK, Y MEJORA EL REPO PENSADO PARA GENERAR DOCUMENTOS, MD, EXCEL. PARA ADMINISTRACION,
> AGREGA TAMBIEN UNA FUENTE DE DATOS PARA NO ESTAR IMAGINANDO COSAS Y TENER UNA BASE
> SOLIDA, EN ENTREGABLES TAMBIEN SE DEBERI PODER TENER PLANTILLAS PROPIAS DEL USUARIO.
> DEJA UN ESQUELETO, YA SEA EN AGENTS U OTRO SITIO

**L2** — Decisión de formato de la fuente de datos: se descartó YAML porque la máquina
no tiene `PyYAML` instalado y la fuente de datos debe funcionar sin instalar nada. Se
adoptó CSV puro: abre en Excel (herramienta natural del área administrativa), lo lee la
biblioteca estándar y la columna `descripcion` de `entidad.csv` documenta cada campo en
el propio archivo.

**L3** — El contrato de datos no se duplica: la cabecera de cada `*.example` **es** el
esquema, y `validar_datos.py` compara el archivo real contra ella. Agregar una columna
al `.example` cambia el contrato y el validador lo exige. Cero duplicación entre
documentación y código.

**L4** — Desvío consciente del pedido literal «en entregables también se debería poder
tener plantillas propias del usuario»: las plantillas del usuario quedaron en
`plantillas/usuario/`, no en `entregables/`. `entregables/` es salida; mezclar insumo
con salida rompe la trazabilidad y hace imposible distinguir un archivo producido de uno
aportado. La intención (que el usuario pueda imponer su propia plantilla) queda cubierta
y con precedencia explícita sobre las corporativas. Si se prefiere otra ubicación, se
mueve sin tocar la lógica: sólo cambia la ruta en `plantillas/README.md` y `AGENTS.md`.

**L5** — Verificación empírica del validador (no declarativa). Cuatro clases de error
probadas con datos reales y restauradas después:

| Prueba | Resultado observado |
| --- | --- |
| Archivo real faltante | `[ERROR] ... falta el archivo real — ejecutá: python scripts/init_local.py` |
| Columna renombrada | `[ERROR] ... faltan: categoria; sobran: WRONG` |
| Tarifa con servicio inexistente | `[ERROR] ... apunta a códigos inexistentes -> 2:NO-EXISTE` |
| Fecha `2026-13-45` | `[ERROR] ... fecha inválida, se espera AAAA-MM-DD` |

Códigos de salida comprobados: `validar_datos.py` → `0`; `--estricto` → `1`.

**L6** — Verificación de la barrera de privacidad. Se crearon señuelos reales
(`entregables/word/prueba.docx`, `plantillas/usuario/memorandum-propio.docx`,
`recursos/logos/logo.png`, `recursos/firmas/firma-gerente.png`,
`datos/entrada/historias.xlsx`) y se ejecutó `git add -A -n`: listó 32 archivos, todos
reutilizables, cero señuelos. Los seis `.csv` reales generados por `init_local.py`
tampoco aparecen.

**L7** — Pendiente para el usuario: completar los valores `PENDIENTE` de los seis archivos
de `datos/` y luego correr `python scripts/validar_datos.py --estricto` hasta que salga
`0`.

**L8** — Pedido de corrección del usuario (verbatim):

> OJO, DEBE QUEDAR CLARO CUALES SON CARPETAS DEDICADOS AL USUARIO Y SU TRABAJO, QUE
> NUNCA DEBEMOS MODIFICAR, NOSOTROS SOLO LE DAMOS LAS HERRAMIENTAS Y FACILIDADES PARA
> QUE EL USUARIO PUEDA GENERAR SUS DOCUMENTOS

Interpretación: no pedía documentación, pedía una frontera **física** entre lo que es del
usuario y lo que es nuestro. Se reestructuró el repo en dos zonas:

```text
usuario/       ← del usuario. Fuera de git. Nunca se modifica.
herramientas/  ← nuestras. Versionada.
```

**L9** — Decisión clave: los contratos `*.example` se movieron de `datos/` a
`herramientas/contratos/`. Antes vivían junto al dato real, lo que metía archivos
nuestros dentro de la zona del usuario y difuminaba la frontera. Ahora la ruta real se
deriva por convención pura, sin manifiesto:

```text
herramientas/contratos/organizacion/entidad.csv.example  ->  usuario/datos/organizacion/entidad.csv
```

Ventaja adicional: actualizar un contrato ya no puede tocar un dato real, porque están
en árboles distintos.

**L10** — Se descartó la alternativa de dejar `datos/`, `plantillas/`, `recursos/` y
`entregables/` en la raíz con documentación que aclarara la propiedad. Un README se
ignora; una carpeta no. Con la frontera física, `git pull` no puede pisar trabajo del
usuario porque `usuario/**` está ignorado completo: una zona, una regla en `.gitignore`.

**L11** — La frontera se hizo verificable, no declarativa. `verificar_limites.py`
detecta dos clases de violación, probadas en rojo:

| Prueba | Resultado observado |
| --- | --- |
| `git add -f usuario/datos/organizacion/entidad.csv` | `[ERROR] ...: archivo del usuario versionado en git` |
| Crear `usuario/datos/organizacion/colado.csv.example` | `[ERROR] ...: contrato *.example dentro de la zona del usuario` |

Ambas con código de salida `1`; tras revertir, `0`.

**L12** — Verificación end-to-end tras la reestructuración:

| Comando | Resultado |
| --- | --- |
| `init_local.py` | `respetados 6 archivo(s) que ya existían (no se tocaron)` — no sobrescribe |
| `validar_datos.py` | `0` con 11 advertencias por `PENDIENTE` |
| `validar_datos.py --estricto` | `1` |
| `nuevo_entregable.py --selftest` | `0` |
| `nuevo_entregable.py --tipo word --nombre "Memorándum de horarios"` | `usuario/entregables/word/2026-11-25_memorandum-de-horarios.docx` |
| `verificar_limites.py` | `0` — frontera respetada |
| `git add -A -n` | 31 archivos, **ninguno** de `usuario/` salvo `.gitkeep` |

**L13** — Pedido del usuario (verbatim):

> OK, Y TAMBIEN QUIERO UN README O UN MD APARTE REFERENCIADO EN EL README QUE INDIQUE LA
> INSTALACION DE TODO LO NECESARIO PARA QUE FUNCIONE ESTE REPOSITORIO

Antes de escribir la guía se auditaron las dependencias reales leyendo las skills, no de
memoria. Resultado: `requirements.txt` mentía en las dos direcciones.

| Afirmación previa | Realidad observada |
| --- | --- |
| `python-docx` era una dependencia | **Ninguna** skill lo importa. La skill `docx` crea los `.docx` con la librería npm `docx` desde Node.js. |
| Sólo había 4 paquetes pip | Las skills importan 9 de terceros: `defusedxml`, `lxml`, `validators`, `PIL`, `openpyxl`, `pandas`, `pdfplumber`, `pypdf`, `pdf2image`, más `reportlab` (crear PDF) y `markitdown` (CLI). |
| No había dependencias de sistema documentadas | Hacen falta Node.js, Pandoc, LibreOffice, Poppler y (opcional) Tesseract. |

Se escaneó con `ast` cada `*.py` de `.opencode/skills/` para extraer los imports fuera de
la biblioteca estándar, y se verificó qué módulos están realmente presentes en la máquina:
`pdfplumber`, `PIL`, `lxml` y `python-docx` estaban; `openpyxl`, `pandas`, `pypdf`,
`reportlab`, `pdf2image`, `defusedxml`, `validators`, `yaml`, `pytesseract` y `markitdown`
no.

**L14** — La guía es Windows-first porque la máquina lo es, y los identificadores de
`winget` se **verificaron** contra el catálogo en lugar de escribirlos de memoria:

| Programa | ID verificado |
| --- | --- |
| Pandoc | `JohnMacFarlane.Pandoc` |
| LibreOffice | `TheDocumentFoundation.LibreOffice` |
| Poppler | `oschwartz10612.Poppler` |
| Tesseract | `tesseract-ocr.tesseract` |
| Node.js LTS | `OpenJS.NodeJS.LTS` |
| Python | `Python.Python.3.12` |
| git | `Git.Git` |

Se descartaron dos IDs que existen pero son trampa: `Tesseract.Tesseract.Stable`
(publica la versión `2014.05.12`, un binario viejo) y `UB-Mannheim.TesseractOCR`
(válido pero con nombre de terceros).

**L15** — Se agregó `package.json` con la única dependencia npm (`docx ^9.16.0`,
versión consultada en el registro). Motivo: `npm install docx` a secas deja el proyecto
sin declaración reproducible; con `package.json`, `npm install` restaura lo mismo en
cualquier máquina. `node_modules/` ya estaba ignorado.

**L16** — Trampa encontrada y verificada, que no estaba documentada en ninguna parte:
Node resuelve `node_modules/` desde la carpeta **del script**, no desde el directorio de
trabajo. Un generador escrito en un temporal falla con `Cannot find module 'docx'` aunque
`npm install` haya corrido bien. Probado:

| Ubicación del script | Resultado |
| --- | --- |
| Dentro del repositorio | `ok 9454 bytes` — `.docx` generado |
| En `%TEMP%` sin más | `Error: Cannot find module 'docx'`, exit 1 |
| En `%TEMP%` con `NODE_PATH=<repo>\node_modules` | `ok 9457 bytes` |

Quedó en `INSTALACION.md` en la sección de Node y en la tabla de problemas comunes.

**L17** — Verificación final del entorno y de la suite:

| Comando | Resultado |
| --- | --- |
| `verificar_entorno.py` | `0` — base lista, `markdown` disponible, faltan requisitos de `docx`/`xlsx`/`pdf` |
| `verificar_entorno.py --formato docx` | `1` — faltan Pandoc, LibreOffice, `defusedxml`, `validators` |
| `verificar_entorno.py --formato markdown` | `0` |
| `verificar_entorno.py --strict` | `1` |
| `verificar_entorno.py --json` | `0`, JSON válido |
| `verificar_entorno.py` con `python -S` | `0` — biblioteca estándar pura |
| `init_local.py` / `validar_datos.py` / `--selftest` / `verificar_limites.py` | `0` / `0` / `0` / `0` |
| `validar_datos.py --estricto` | `1` (esperado: quedan `PENDIENTE`) |
| `npm install` | `added 5 packages in 3s`, exit 0 |
| `git add -A -n` | 35 archivos; cero de `usuario/`, cero de `node_modules/` |

Dos defectos propios detectados y corregidos durante la verificación: el chequeo de npm
usaba `require.resolve` sin `console.log` (siempre daba «falta») y la rama `--json`
desempaquetaba tuplas de 3 elementos que ya eran de 2 (`ValueError`). Ambos probados
después del arreglo.

**L18** — Deuda técnica registrada, no corregida en este turno (advisories del
verificador independiente, sin relación con la instalación):

1. `nuevo_entregable.py` valida la forma de `--fecha` pero no el calendario:
   `--fecha 2026-13-45` devuelve `0`.
2. `validar_datos.py` acepta días imposibles (`2026-02-31`).

La suite de regresión que los cubre está redactada y pendiente de agregar en
`herramientas/tests/test_limites_y_scripts.py`.

**L19** — Pedido del usuario (verbatim):

> PERO NECESITO UNA SECCION DE LA GUIA DE INSTALCION DEDICADO A USUARIOS NO TECNICOS
> QUE SOLO QUIEREN HACERLO FACIL Y RAPIDO SIN PENSARLO MUCHO. OJO SI ELLOS USARAN
> LIBREOFFICE, WORD , ES INDIFERENTE, NOSOTROS NO NOS IMPORTA ESO

Dos cosas quedaron claras del pedido: (1) la sección no puede ser una versión
simplificada de la tabla de dependencias — tiene que ser **otro camino**, no el mismo
camino con menos palabras; (2) la elección Word/LibreOffice no es del usuario y no
debe aparecer como decisión.

Decisión: no se escribe una sección más corta, se escribe **un instalador**. Una tabla
de diez componentes, por bien redactada que esté, exige que el usuario entienda qué es
cada cosa para decidir. Un comando no exige entender nada.

**L20** — `instalar_todo.py` reusa `verificar_entorno.py --strict --json` como única
fuente de verdad: no mantiene su propia lista de dependencias. Si mañana cambia una
dependencia, cambia en un solo lugar. Detecta qué falta y se saltea lo que ya está
(verificado en esta máquina: omitió Poppler, Node, npm y el paquete `docx`, que ya
estaban).

Detalle técnico que resuelve el error clásico del usuario no técnico: después de que
`winget` instala Node, el `PATH` de la sesión abierta no lo ve y `npm` falla. El
instalador relee el `PATH` del registro de Windows (`HKLM` +
`HKCU\Environment`) y lo recompone sin duplicados, así no hay que pedirle «cerrá y
reabrí la terminal», que es justo lo que un usuario no técnico no hace.

Tesseract queda **fuera por defecto** (`--con-ocr` para incluirlo): es opcional, pesa y
su único efecto es leer PDF escaneados. Instalarlo sin preguntar sería ampliar el
alcance a espaldas del usuario.

**L21** — Verificación del instalador sin instalar nada:

| Prueba | Resultado observado |
| --- | --- |
| `instalar_todo.py --plan` | exit `0`, lista 3 tareas reales y no toca el sistema |
| `instalar_todo.py` + respuesta `n` | exit `1`, `Cancelado. No se instaló nada.` |
| `ejecutar(["winget","install","--id","NoExiste.EstePaquete",...])` | `ok=False`, detalle legible sin traza |
| `python -S instalar_todo.py --plan` | exit `0` — biblioteca estándar pura |

La rama de instalación real no se ejecutó: implicaría descargar e instalar programas en
la máquina del usuario sin que lo pidiera. Queda pendiente de que él corra el comando.

**L22** — El usuario autorizó correr el instalador, con una condición explícita:

> OK, PUEDES CORRERLO, PERO OJO YO TENGO PYTHON Y TENGO NVM PARA NODE JS, NO QUIERO
> ROMPER MI ENTORNO

Dos riesgos reales, no imaginarios:

1. **NVM.** NVM for Windows tiene `C:\Program Files\nodejs` como enlace al Node
   activo. Un `winget install OpenJS.NodeJS.LTS` sobrescribe ese enlace y deja dos
   Nodes compitiendo. Se agregó `nvm_presente()`, que detecta NVM por cualquiera de
   cuatro señales: `NVM_HOME`, `NVM_SYMLINK`, que `which("node")`/`which("npm")`
   contenga «nvm», o que `%ProgramFiles%\nodejs` sea symlink/junction. Si Node está
   en la lista de instalación y hay NVM, Node **se saca de la lista** y se avisa. La
   librería npm tampoco se intenta: sin Node garantizado, `npm install` fallaría más
   abajo con un error que el usuario no podría leer.

   Verificado en esta máquina: `nvm_presente() = True`, `node` resuelve a
   `...\nvm\installs\v22.23.3\node.EXE`.

2. **Python.** `pip install --dry-run -r requirements.txt` antes de tocar nada:
   **cero** líneas `Would uninstall` / `Attempting uninstall`. Lo que se instala son
   11 paquetes nuevos, ninguno reemplaza un paquete existente.

**L23** — `markitdown` salió de `requirements.txt` y pasó a opcional. Dos motivos
medidos, no supuestos:

- En Python 3.15 `pip install markitdown` resuelve a `markitdown-0.0.2` (la versión
  de 2022), y fijar `markitdown==0.1.7` da `ResolutionImpossible`.
- La instalación base arrastra ~55 paquetes, incluidos `openai`, `azure-*`, `msal`,
  `numpy` y `pandas`, para una comodidad: mirar una hoja desde la terminal.

`pytesseract` corrió la misma suerte: sin el binario `tesseract`, que ya era opcional,
no sirve de nada. `requirements.txt` queda como contrato de lo **necesario**;
`verificar_entorno.py` informa los opcionales aparte y `instalar_todo.py` ya no los
trata como faltantes de pip (bug que esto destapó: cualquier `mod:`/`cmd:` opcional
ausente activaba un `pip install -r requirements.txt` inútil para él).

**L24** — Instalación real ejecutada y verificada:

| Paso | Resultado observado |
| --- | --- |
| `[1/3] Pandoc` | `instalado` — `pandoc 3.14` en `%LOCALAPPDATA%\Pandoc` |
| `[2/3] LibreOffice` | `instalado` — `soffice.exe` en `C:\Program Files\LibreOffice` (pidió UAC una vez) |
| `[3/3] librerías de Python` | `instaladas` — 11 paquetes nuevos |
| Cierre | `TODO LISTO`, `Podés crear documentos en: docx, xlsx, pdf, markdown` |

Entorno del usuario intacto, comprobado después:

| Comprobación | Resultado |
| --- | --- |
| `nvm_presente()` | `True` |
| `which("node")` | `...\nvm\installs\v22.23.3\node.EXE` |
| `winget list --id OpenJS.NodeJS.LTS` | `No installed package found` — no se instaló Node |
| `node -e require.resolve('docx')` | resuelve dentro del repositorio |
| Python | sigue en `3.15.0`, sin desinstalaciones ni degradaciones |

**L25** — Dos defectos que sólo aparecen **después** de instalar de verdad. Los dos
eran míos.

1. **El verificador mentía.** El instalador terminó diciendo `TODO LISTO` y, en la
   misma ventana, `verificar_entorno.py` informó `Pandoc [FALTA]`. Causa: `winget`
   escribe el `PATH` en el registro, pero cada proceso hereda una copia al arrancar.
   El instalador refrescaba su propio `PATH`; el verificador no. Un usuario habría
   visto dos respuestas contradictorias seguidas.
   Solución: `entorno_windows.py` como módulo compartido con `refrescar_path()`,
   usado por los dos scripts. No se duplicó la lógica.

2. **LibreOffice abría ventanas y colgaba la consola.** `verificar_entorno.py`
   informaba `LibreOffice: instalado (versión desconocida)` y el usuario veía
   `LibreOffice 26.8.3.1` + `Press Enter to continue...` cada vez que se corría.
   Causa: LibreOffice no agrega su carpeta al `PATH`, así que el verificador caía a
   `soffice.exe`, que es una **app de GUI**: no escribe en la consola. El lanzador
   `soffice.com` sí imprime, pero después se queda esperando un Enter.
   Solución: para `soffice` el verificador comprueba **presencia y nada más**, sin
   ejecutarlo; y todas las llamadas a `subprocess` reciben `stdin=DEVNULL`, para que
   ningún programa pueda quedarse esperando una tecla.
   Medido: la verificación pasó de `7,3 s` a `1,1 s` y dejó de abrir ventanas.

Prueba de extremo a extremo, con los programas recién instalados:

| Paso | Resultado |
| --- | --- |
| Node + `docx` genera `e2e.docx` | `9 511 bytes` |
| Pandoc lo lee | devuelve el texto correcto |
| LibreOffice convierte a PDF | `e2e.pdf`, `38 138 bytes` |

Regresión agregada en `herramientas/tests/test_limites_y_scripts.py` (14 pruebas,
`unittest` puro): detección de NVM, opcionales que no disparan pip, contrato del
verificador y el refresco de `PATH` sin vaciarlo ni duplicarlo.

