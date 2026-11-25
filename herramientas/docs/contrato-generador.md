# Contrato de generadores propios del usuario

El usuario puede tener **su propia plantilla** y usarla para **todos** sus
documentos. Si esa plantilla es código —un `.py` o un `.js`—, ese código es
suyo: vive en la zona del usuario, no se versiona, no lo modifica el agente y el
proyecto no lo importa.

El proyecto publica **sólo el contrato** que permite usar ese código. Eso es
todo.

```text
usuario/generadores/<nombre>/
  generador.json     # manifiesto: qué tipos cubre y cómo se ejecuta
  generador.py       # (o generador.js) el código del usuario
  README.md          # opcional: notas del usuario
```

## Precedencia

Cuando el motor genera un documento, el formato se resuelve en este orden:

1. **Generador propio del usuario** que declare el tipo.
2. Plantilla binaria propia: `usuario/plantillas/propias/<tipo>-*`.
3. Plantilla oficial: `usuario/plantillas/oficiales/<tipo>-*`.
4. Membrete declarado en `usuario/datos/organizacion/entidad.csv`.
5. Formato por defecto del motor (`renderizar_docx.js`).

Ojo con quién implementa cada paso: **el motor implementa el paso 1 y el 5**. O
usa tu generador, o usa el renderizador genérico. Los pasos 2 a 4 son convención
de redacción del agente (ver `herramientas/docs/flujo-de-trabajo.md`): el motor
declarativo no abre plantillas binarias ni lee el membrete.

El motor **siempre** resuelve el contenido (placeholders, tablas, bloques
repetidos, índice, `PENDIENTE`). El generador propio aplica **el formato**:
membrete, tipografía, color, sellos, firmas, encabezados.

Si dos generadores declaran el mismo tipo explícito, o si dos declaran sólo
`"*"`, el motor falla y lo dice: la ambigüedad se reporta, no se resuelve en
silencio.

## El manifiesto `generador.json`

```json
{
  "nombre": "corporativo",
  "descripcion": "Identidad visual de la empresa para todo tipo de documento",
  "tipos": ["*"],
  "script": "generador.py",
  "comando": ["python"]
}
```

| Campo | Obligatorio | Qué significa |
| --- | --- | --- |
| `tipos` | Sí | Tipos de documento que cubre. `"*"` significa **todos**. |
| `nombre` | No | Nombre del generador. Por defecto, el nombre de la carpeta. |
| `descripcion` | No | Texto libre para que el usuario se ubique. |
| `script` | No | Archivo a ejecutar, relativo a la carpeta. Por defecto `generador.py` o `generador.js`, si existen. |
| `comando` | No | Intérprete y sus argumentos. Por defecto `["python"]` para `.py` y `["node"]` para `.js`. |

Reglas del manifiesto:

- Un tipo explícito gana sobre `"*"`. La ambigüedad falla sólo si dos
  generadores declaran el **mismo** tipo explícito, o si dos declaran `"*"`.
- `script` no puede ser absoluto ni salir de la carpeta del generador.
- El manifiesto se lee con `utf-8-sig`: un BOM de Windows no lo rompe.
- **Un manifiesto roto no rompe el resto.** Si un `generador.json` es inválido,
  ese generador se saltea y se reporta; los demás tipos se siguen generando con
  el renderizador genérico. `listar_generadores.py` muestra los rotos con su
  error y sale con código `1`.

## El payload

El motor arma un `payload.json` y se lo entrega al generador:

```json
{
  "version": 1,
  "tipo": "manual",
  "titulo": "Manual de Organización y Funciones",
  "formato": "docx",
  "pie": "Manual de Organización y Funciones · v1.0",
  "salida": "usuario/entregables/word/2026-11-25_manual.docx",
  "bloques": [ ... ],
  "indice": [ { "texto": "I. Objeto", "pagina": 1 } ],
  "entidad": { "razon_social": "ACME S.A.C." },
  "datos": { "entidad": { "cabecera": [...], "filas": [...] } },
  "constantes": { "anio": "2026" }
}
```

| Campo | Qué es |
| --- | --- |
| `salida` | Ruta **relativa a la raíz del repositorio** donde el generador debe escribir el archivo. |
| `bloques` | El contenido ya resuelto: sin placeholders, sin `PENDIENTE` en lo que el documento usa. |
| `indice` | Las entradas del índice, con su número de página. |
| `entidad` | Los campos de `organizacion/entidad.csv` como mapa, para el membrete. |
| `datos` | Los CSV crudos, en la misma forma que los lee el motor: `{ "cabecera": [...], "filas": [...] }`. |
| `constantes` | Las constantes de la spec (por ejemplo `anio`). |

`datos` va aparte a propósito: el generador puede aplicar su plantilla a
campos que el motor no usó. Si usa un campo con `PENDIENTE`, **es su
responsabilidad** no dejarlo pasar.

### Tipos de bloque

Los bloques del payload son los que entiende el renderizador genérico. Un
generador propio puede usar todos, algunos o ninguno:

| `tipo` | Campos | Qué produce |
| --- | --- | --- |
| `portada` | `lineas[]` con `texto`, `tamano`, `negrita`, `cursiva`, `color` | Líneas centradas de portada. |
| `titulo` | `texto`, `nivel` (1-3) | Título de sección. |
| `parrafo` | `texto`, `cursiva`, `tamano` | Párrafo. |
| `lista` / `numerada` | `items[]`, `numerada` | Lista con viñetas o numerada. |
| `tabla` | `encabezado[]`, `filas[][]`, `anchos[]`, `encabezado_azul`, `primera_negrita` | Tabla. |
| `indice` | — | Índice, con la página de cada entrada de `indice`. |
| `firma` | `cargo`, `entidad`, `texto` | Bloque de firma. |
| `pagina` | — | Salto de página. |

Un bloque desconocido es un error: el motor no adivina.

## La invocación

El motor corre el generador así:

```bash
<comando> <ruta del script> --entrada <ruta del payload.json>
```

- El **directorio de trabajo** es la raíz del repositorio. Por eso
  `payload["salida"]` es relativa a esa raíz.
- El generador **escribe** el archivo en `payload["salida"]`.
- Código de salida `0` = todo bien. Cualquier otro = error, y el motor muestra
  la salida estándar del generador tal cual.
- Si el generador termina bien pero no dejó el archivo, es error igual.

El generador se ejecuta como **subproceso**: el motor nunca lo importa. Un
error del generador del usuario no rompe el motor genérico.

Límites que pone el motor:

- **Zona**: sólo se ejecuta código que viva dentro de `usuario/generadores/`.
  `--generador` acepta una ruta relativa a la raíz del repositorio (o absoluta),
  pero si apunta fuera de esa carpeta el motor la rechaza.
- **Tiempo**: 180 segundos. Al vencerlo, el motor corta el proceso y reporta el
  error; no queda un `.docx` a medias.
- **Salida parcial**: si el generador falla después de escribir, el motor borra
  ese archivo. Nunca toca un entregable que ya existía: la ruta destino se
  valida como nueva antes de ejecutar.

## Ejemplo mínimo

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--entrada", required=True)
args = parser.parse_args()

payload = json.loads(Path(args.entrada).read_text(encoding="utf-8"))
salida = Path(payload["salida"])
salida.parent.mkdir(parents=True, exist_ok=True)
salida.write_text(payload["titulo"], encoding="utf-8")
print(f"OK {salida}")
```

Un ejemplo completo y funcional —con identidad visual, membrete, logo, pie con
número de página y control de `PENDIENTE`— está en
`herramientas/ejemplos/generador-corporativo/`. Usa `python-docx`, que ya está
declarado en `requirements.txt`.

## Reglas del generador

1. **No inventes datos.** Todo sale de `payload`.
2. **No dejes `PENDIENTE`** en el documento final, ni en el texto ni en las
   tablas.
3. **No escribas fuera de `payload["salida"]`.**
4. **No modifiques `usuario/datos/`.** Son datos del usuario.
5. **Fallo explícito:** si algo no cierra, salí con código distinto de `0` y
   escribí el motivo en la salida de error.
6. El código es del usuario: el agente no lo edita. Si tiene un defecto, se lo
   muestra con el error exacto y le propone el arreglo.

## Comandos

```bash
python herramientas/scripts/listar_generadores.py            # qué hay
python herramientas/scripts/listar_generadores.py --json     # para scripts

python herramientas/scripts/generar_documento.py --tipo manual
python herramientas/scripts/generar_documento.py --tipo manual --sin-generador
python herramientas/scripts/generar_documento.py --tipo manual --generador usuario/generadores/corporativo
```

- `--sin-generador` ignora los generadores propios y usa el renderizador
  genérico.
- `--generador <carpeta>` fuerza uno concreto; si no declara el tipo, el motor
  falla en vez de adivinar. La ruta se resuelve contra la raíz del repositorio,
  así que funciona igual desde cualquier directorio.
- `--generador` y `--sin-generador` son excluyentes: si pedís las dos, el
  comando falla en vez de descartar una en silencio.

## Zona y privacidad

`usuario/` está fuera de git: el generador del usuario nunca se versiona ni
sale de su máquina. El proyecto versiona **el contrato**, no el código.

`verificar_limites.py` falla si aparece un archivo del usuario versionado.
