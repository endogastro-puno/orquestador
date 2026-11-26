# Scripts

Herramientas reutilizables. **Sólo trabajan sobre `herramientas/` y `usuario/`, y
nunca modifican lo que el usuario ya tiene.**

| Script | Qué hace | Escribe en la zona del usuario |
| --- | --- | --- |
| `init_local.py` | Crea las carpetas de `usuario/` y copia cada contrato a su archivo real | Sólo archivos que **no existen**. Nunca sobrescribe. |
| `validar_datos.py` | Valida `usuario/datos/` contra `herramientas/contratos/` | **No escribe nada** |
| `nuevo_entregable.py` | Resuelve la ruta `usuario/entregables/<tipo>/AAAA-MM-DD_slug.ext` | Sólo crea la carpeta destino |
| `verificar_limites.py` | Comprueba que nada de `usuario/` esté versionado | **No escribe nada** |
| `verificar_entorno.py` | Comprueba que estén instaladas las dependencias de cada formato | **No escribe nada** |
| `instalar_todo.py` | Instala lo que falte (Windows, `winget` + pip + npm) | **No escribe nada** |
| `generar_documento.py` | Genera `.docx` desde un spec declarativo y los CSV | Crea un entregable nuevo; **nunca sobrescribe**. `--salida` se rechaza si el archivo existe o queda fuera de `usuario/entregables/` |
| `listar_generadores.py` | Lista los generadores propios del usuario y los tipos que cubren | **No escribe nada**. Sólo lee `usuario/generadores/` |
| `leer_documento.py` | Lee `.docx`, `.pdf`, `.xlsx`, `.csv`, `.md`, `.txt` e imágenes (OCR); devuelve texto y estructura | **No escribe nada**. Sólo lee |
| `menu.py` | Menú que lista y corre todas las facilidades; `--opcion N` las corre directo | **No escribe nada**. Sólo corre otros scripts |
| `indexar_documentos.py` | Mapea una carpeta completa y guarda el índice incremental en `usuario/indice/` | Sólo escribe el índice (regenerable); **los originales jamás se tocan** |
| `buscar_documentos.py` | Consulta el índice: por nombre y por contenido, con filtros `--tipo`, `--carpeta`, `--escaneados` | **No escribe nada**. Sólo lee el índice |
| `instalar_plantilla.py` | Copia una plantilla que el usuario ya tiene a `plantillas/propias/` (o `oficiales/`) con el nombre canónico `<tipo>-<variante>.<ext>` | Sólo crea un archivo que **no existe**, con un `--origen` que el usuario pasa explícitamente. Nunca sobrescribe |
| `nueva_plantilla.py` | Crea una plantilla inicial sobria (`.docx`, `.xlsx` o `.md`) para un tipo | Sólo crea un archivo que **no existe**. Nunca sobrescribe |
| `selftest.py` | Prueba de humo: genera un documento en un temporal y comprueba el motor | **No escribe nada** en el repositorio |

`renderizar_docx.js` es el único renderizador de Word: recibe un payload JSON ya
resuelto y no contiene datos de empresa. `generar_documento.py` es el que resuelve
placeholders, expande tablas y bloques repetidos, calcula el índice y llama al renderer.

`generadores_usuario.py` es un módulo, no un script: implementa el contrato de los
generadores propios del usuario (descubrimiento, payload, invocación como
subproceso). El contrato, en detalle, está en
`herramientas/docs/contrato-generador.md`.

`workspace.py` es el módulo que resuelve el **espacio de trabajo**: `--workspace` >
`ORQUESTADOR_WORKSPACE` > `<repo>/usuario`. Todos los comandos que tocan la zona del
usuario lo usan, así que apuntar los datos a otra carpeta no cambia ninguna ruta por
dentro.

`plantillas.py` es el módulo compartido de plantillas: el catálogo de tipos, la
extensión válida para cada uno, el nombre canónico `<tipo>-<variante>.<ext>` y el
contrato de copia. Lo usan `instalar_plantilla.py`, `nueva_plantilla.py` y `menu.py`,
para que esas reglas vivan en un solo lugar. Su contrato de escritura es el de
`init_local.py`: crea un archivo que no existe; si ya existe, se rechaza con mensaje
explícito (dos plantillas del mismo tipo romperían la precedencia, así que no hay
`-v2` silencioso).

`menu.py` no duplica lógica: cada opción corre OTRO script de esta carpeta como
subproceso y devuelve su código de salida tal cual. Los tipos declarativos que
ofrece descubrirlos de `herramientas/contratos/tipos/*.json`, no de una lista fija.

`indexar_documentos.py` y `buscar_documentos.py` tampoco duplican lectura de
formatos: el indexador usa los lectores de `leer_documento.py` (OOXML, pdfplumber,
openpyxl, OCR) y guarda un JSON por raíz en `usuario/indice/`. El índice es
incremental — compara tamaño y fecha, relee sólo lo que cambió — y marca los PDF
escaneados para que `buscar_documentos.py --escaneados` los encuentre. Nunca se
versiona: contiene texto de documentos privados del usuario.

Los scripts de Python usan sólo la biblioteca estándar de Python 3.10+, salvo
`generar_informe_ejecutivo.py` y los generadores propios del usuario (el ejemplo
incluido), que usan `python-docx` — declarado en `requirements.txt`. Las skills de
generación documental sí necesitan más dependencias: ver `INSTALACION.md` en la raíz.

`entorno_windows.py` no es un script sino un módulo compartido: expone
`refrescar_path()`, que relee el `PATH` del registro de Windows. Lo usan
`instalar_todo.py` y `verificar_entorno.py`, porque un programa recién instalado con
`winget` no aparece en la ventana que ya estaba abierta. Sin eso, el instalador
terminaría diciendo «listo» y el verificador, en la misma ventana, diría que falta
todo.

## Pruebas

```bash
python -m unittest discover -s herramientas/tests -v
```

Sólo biblioteca estándar: no hace falta instalar `pytest` ni nada más. Cubren la
detección de NVM, el trato de los requisitos opcionales, el contrato del
verificador, el motor, los generadores propios, los lectores de documentos, las
facilidades de plantillas y menú, y el índice de documentos. Las pruebas de
`.pdf`, `.xlsx` y OCR se saltean solas si falta la dependencia del formato.

En Windows, si `python` apunta a una versión vieja, usá el lanzador: `py -3`.
El repositorio necesita **Python 3.10 o superior**.

## Uso rápido

```bash
python herramientas/scripts/instalar_todo.py --plan   # qué falta, sin instalar
python herramientas/scripts/instalar_todo.py          # instala y verifica
python herramientas/scripts/verificar_entorno.py
python herramientas/scripts/verificar_entorno.py --formato docx

python herramientas/scripts/init_local.py
python herramientas/scripts/validar_datos.py
python herramientas/scripts/validar_datos.py --estricto
python herramientas/scripts/verificar_limites.py

python herramientas/scripts/nuevo_entregable.py --tipo word --nombre "Memorándum de horarios"
python herramientas/scripts/nuevo_entregable.py --tipo excel --nombre "Tarifas 2026" --json
python herramientas/scripts/nuevo_entregable.py --selftest

python herramientas/scripts/listar_generadores.py
python herramientas/scripts/generar_documento.py --tipo manual
python herramientas/scripts/generar_documento.py --tipo manual --sin-generador

python herramientas/scripts/leer_documento.py usuario/datos/entrada/informe.docx --json
python herramientas/scripts/leer_documento.py planilla.xlsx --texto
python herramientas/scripts/leer_documento.py escaneo.png --texto

python herramientas/scripts/menu.py
python herramientas/scripts/menu.py --opcion 5 -- contrato.docx --json
python herramientas/scripts/instalar_plantilla.py --origen membrete.docx --tipo oficio --variante Corporativa
python herramientas/scripts/nueva_plantilla.py --tipo informe
python herramientas/scripts/nueva_plantilla.py --selftest
python herramientas/scripts/instalar_plantilla.py --selftest
python herramientas/scripts/menu.py --selftest

python herramientas/scripts/indexar_documentos.py --ruta D:\FOLDER-PRINCIPAL
python herramientas/scripts/buscar_documentos.py "cotización" --tipo docx,pdf
python herramientas/scripts/buscar_documentos.py --escaneados
python herramientas/scripts/indexar_documentos.py --selftest
python herramientas/scripts/buscar_documentos.py --selftest

python herramientas/scripts/selftest.py

# La misma herramienta, con los datos en otra carpeta:
python herramientas/scripts/init_local.py --workspace D:\clientes\clinica-a
python herramientas/scripts/validar_datos.py --workspace D:\clientes\clinica-a
```

Códigos de salida: `0` correcto, `1` error. Esto permite encadenarlos en el flujo sin
interpretar texto.

## Reglas para scripts nuevos

1. **Nunca escribir en `usuario/datos/`, `usuario/plantillas/`, `usuario/recursos/` ni
   `usuario/generadores/`.**
   Es la regla que define este repositorio; un script que la rompe es un defecto.
   La única excepción es el contrato de `init_local.py`: crear un archivo que **no
   existe**, pedido explícitamente por el usuario (`--origen` de
   `instalar_plantilla.py`, contratos de `init_local.py`). Nunca editar, mover ni
   borrar lo que ya está. En `usuario/generadores/` el agente sólo **ejecuta** el
   código del usuario.
2. Sólo biblioteca estándar, salvo que la tarea lo justifique; en ese caso se agrega la
   dependencia a `requirements.txt`.
3. Sin rutas absolutas ni datos incrustados: todo se lee de los contratos, de
   `usuario/` o de argumentos.
4. Sin nombres reales, RUC, precios ni identificadores en el código, ni en ejemplos.
5. Las rutas de las herramientas salen de `workspace.RAIZ` (calculada desde
   `__file__`). Las de la zona del usuario salen de `workspace.resolver(...)`:
   nunca escribas `RAIZ / "usuario"` a mano, porque ignora `--workspace`.
6. Si el script tiene lógica no trivial, incluí un `--selftest` que no toque el
   repositorio (usá `tempfile`).
7. Documentá el contrato en el docstring del módulo, no en comentarios sueltos.
8. Código de salida explícito y mensajes en español neutro.
