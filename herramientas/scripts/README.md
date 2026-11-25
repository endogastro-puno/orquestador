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
| `generar_documento.py` | Genera `.docx` desde un spec declarativo y los CSV | Crea un entregable nuevo; **nunca sobrescribe** |

`renderizar_docx.js` es el único renderizador de Word: recibe un payload JSON ya
resuelto y no contiene datos de empresa. `generar_documento.py` es el que resuelve
placeholders, expande tablas y bloques repetidos, calcula el índice y llama al renderer.

Los siete scripts de Python usan sólo la biblioteca estándar de Python 3.10+. Las skills de generación
documental sí necesitan dependencias: ver `INSTALACION.md` en la raíz.

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
detección de NVM, el trato de los requisitos opcionales y el contrato del verificador.

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
```

Códigos de salida: `0` correcto, `1` error. Esto permite encadenarlos en el flujo sin
interpretar texto.

## Reglas para scripts nuevos

1. **Nunca escribir en `usuario/datos/`, `usuario/plantillas/` ni `usuario/recursos/`.**
   Es la regla que define este repositorio; un script que la rompe es un defecto.
2. Sólo biblioteca estándar, salvo que la tarea lo justifique; en ese caso se agrega la
   dependencia a `requirements.txt`.
3. Sin rutas absolutas ni datos incrustados: todo se lee de los contratos, de
   `usuario/` o de argumentos.
4. Sin nombres reales, RUC, precios ni identificadores en el código, ni en ejemplos.
5. Rutas relativas a la raíz del repositorio, calculadas desde `__file__`
   (`RAIZ = Path(__file__).resolve().parents[2]`).
6. Si el script tiene lógica no trivial, incluí un `--selftest` que no toque el
   repositorio (usá `tempfile`).
7. Documentá el contrato en el docstring del módulo, no en comentarios sueltos.
8. Código de salida explícito y mensajes en español neutro.
