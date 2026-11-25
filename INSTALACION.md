# Instalación

Todo lo que hay que instalar en la máquina para que este repositorio genere
documentos. Esta guía **no toca tus datos**: no escribe nada dentro de
`usuario/`.

---

## Instalación sin vueltas

**Si no sos técnico y sólo querés que funcione: esta es tu sección.** No hace
falta leer nada más.

### Lo único que tenés que hacer

1. Abrí la carpeta del proyecto en el Explorador de Windows.
2. **Clic derecho** en un espacio vacío de la carpeta → **Abrir en Terminal**.
   - En Windows 10: mantené **Shift**, clic derecho → **Abrir ventana de
     PowerShell aquí**.
3. Se abre una ventana negra o azul. **Pegá esta línea** (clic derecho pega) y
   apretá **Enter**:

   ```powershell
   python herramientas/scripts/instalar_todo.py
   ```

4. Te va a mostrar una lista de lo que va a instalar. Escribí **`S`** y apretá
   **Enter**.
5. Windows te va a pedir permiso para instalar programas. **Aceptá** (decir que
   sí).
6. Esperá. Puede tardar entre **5 y 20 minutos** según tu internet. **No cierres
   la ventana** y no aprietes teclas mientras trabaja.

### Cómo sé si terminó bien

Buscá esta palabra al final de todo:

```text
TODO LISTO
```

| Lo que ves al final | Qué significa | Qué hacés |
| --- | --- | --- |
| `TODO LISTO` | Ya está. Podés crear documentos. | Seguí con el paso de abajo. |
| `FALTAN COSAS` | Algo no se pudo instalar. | Copiá todo el texto y pegáselo al agente. |
| `python no se reconoce...` | Falta Python en la computadora. | Pedile al agente: «no tengo Python instalado, instalalo y seguí». |
| La ventana se cerró sola | Se cortó la instalación. | Volvé a empezar desde el paso 3. |

### Y ahora qué

Abrí el agente (OpenCode) en esta carpeta y pedile un documento como se lo
pedirías a una persona:

> Redactá un memorándum de actualización de horarios y guardalo en Word.

**No tenés que decidir nada más.** Ni qué programa usar, ni si es Word o
LibreOffice, ni en qué formato guardarlo: eso lo resuelve el agente. Tampoco
tenés que tener Word instalado.

### Si algo sale mal

No hace falta que entiendas el error ni que lo investigues. Copiá el texto
completo de la pantalla y pegáselo al agente con esta frase:

> Esto falló al instalar. Arreglalo y volvé a intentar.

Para eso está el agente. Pelearte con la terminal es trabajo suyo, no tuyo.

### Qué hace ese comando, en una frase

Mira qué le falta a la computadora, instala **sólo eso**, y al final te dice si
quedó listo. No borra nada, no cambia tus archivos y no toca tus datos.

Lo que sigue en esta guía es el detalle para quien quiere entender qué se
instala y por qué. **No hace falta leerlo para que funcione.**

---

## Camino corto

Para quien ya tiene Python, Node.js y git:

```powershell
cd C:\ruta\al\orquestador

python -m pip install -r requirements.txt
npm install

python herramientas/scripts/verificar_entorno.py
```

Si el verificador termina con `entorno listo para todos los formatos`, está
todo. Si no, te dice exactamente qué falta y cómo se instala.

Alternativa: `python herramientas/scripts/instalar_todo.py --plan` muestra qué
falta y `python herramientas/scripts/instalar_todo.py --si` lo instala sin
preguntar.

## Qué se instala y para qué

> Tabla de referencia. Si usaste el instalador de la sección anterior, todo esto
> ya está resuelto y no tenés que hacer nada.

| Componente | Se instala con | Para qué | ¿Obligatorio? |
| --- | --- | --- | --- |
| **Python 3.10+** | `winget install Python.Python.3.12` | Scripts del repositorio y skills de PDF/Excel | **Sí** |
| **git** | `winget install Git.Git` | Versionado, `verificar_limites.py` | **Sí** |
| **Paquetes de Python** | `python -m pip install -r requirements.txt` | openpyxl, pandas, pypdf, reportlab, pdfplumber, pdf2image, Pillow, lxml, defusedxml, validators | **Sí** |
| **Node.js + npm** | `winget install OpenJS.NodeJS.LTS` | Generar `.docx` y leerlos | Sí, para Word |
| **Paquete npm `docx`** | `npm install` | Crear documentos `.docx` | Sí, para Word |
| **Pandoc** | `winget install JohnMacFarlane.Pandoc` | Leer `.docx` y convertir a Markdown | Sí, para Word |
| **LibreOffice** | `winget install TheDocumentFoundation.LibreOffice` | Convertir a PDF, recalcular fórmulas de Excel, aceptar cambios | Sí, para Word/Excel/PDF |
| **Poppler** | `winget install oschwartz10612.Poppler` | `pdftoppm`: renderizar páginas para revisarlas | Sí, para Word/PDF |
| **Tesseract OCR** | `winget install tesseract-ocr.tesseract` | Leer PDF escaneado (imagen) | No, sólo OCR |
| **`pytesseract`** | `python -m pip install pytesseract` | Puente Python → Tesseract | No, sólo OCR |
| **`markitdown`** | `python -m pip install markitdown` | Vistazo rápido de una hoja desde la terminal | No, comodidad |

### Una aclaración que evita perder tiempo

**`python-docx` no se usa.** La skill `docx` genera los `.docx` desde Node.js
con la librería npm `docx`, y los lee con Pandoc. Si alguien te dice que
instales `python-docx`, no aplica a este repositorio.

Tampoco hace falta tener Microsoft Word ni Excel instalados. Qué programa de
oficina uses es indiferente: LibreOffice se instala sólo para las conversiones y
no reemplaza ni modifica nada de lo que ya tengas.

## Windows, paso a paso

Los comandos están verificados contra `winget`. Se ejecutan en **PowerShell**.

### 1. Programas base

```powershell
winget install Git.Git
winget install Python.Python.3.12
winget install OpenJS.NodeJS.LTS
```

Si ya tenés Python 3.10 o superior, no lo instales de nuevo. Versiones 3.11 o
3.12 son las más seguras para estas librerías: las más nuevas a veces todavía
no tienen binarios precompilados de `pandas`.

**Cerrá y reabrí la terminal** después de instalar: los programas recién
agregados al `PATH` no aparecen en una sesión ya abierta.

### 2. Programas de documentos

```powershell
winget install JohnMacFarlane.Pandoc
winget install TheDocumentFoundation.LibreOffice
winget install oschwartz10612.Poppler
```

Opcional, sólo si vas a leer PDF escaneados:

```powershell
winget install tesseract-ocr.tesseract
```

### 3. Dependencias de Python

```powershell
cd C:\ruta\al\orquestador
python -m pip install -r requirements.txt
```

Si `pip` falla con `Could not find a version that satisfies the requirement
pandas` o `no matching distribution`, es la versión de Python. Solución con un
entorno virtual sobre 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`.venv/` ya está en `.gitignore`, no se versiona. Cada vez que abras una
terminal nueva para trabajar en el repositorio, activalo:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Dependencia de Node

```powershell
npm install
```

Instala `docx` desde `package.json` y crea `node_modules/`, que está ignorado
por git.

**Dónde tiene que estar el script que genera el `.docx`.** Node busca
`node_modules/` partiendo de la carpeta **del script**, no de la carpeta desde
donde lo ejecutás. Verificado:

| Ubicación del script | ¿Encuentra `docx`? |
| --- | --- |
| Dentro del repositorio | Sí |
| Fuera (un temporal, por ejemplo) | No, salvo que definas `NODE_PATH` |

Si el script va fuera del repositorio, apuntá `NODE_PATH` a `node_modules`:

```powershell
$env:NODE_PATH = "C:\ruta\al\orquestador\node_modules"
node C:\tmp\script.js
```

### 5. Verificar

```powershell
python herramientas/scripts/verificar_entorno.py
```

## Linux y macOS

Equivalentes, sin `winget`.

**Debian / Ubuntu**

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv nodejs npm pandoc \
                    libreoffice poppler-utils tesseract-ocr
python3 -m pip install -r requirements.txt
npm install
```

**Fedora**

```bash
sudo dnf install -y git python3 python3-pip nodejs npm pandoc libreoffice \
                    poppler-utils tesseract
```

**macOS (Homebrew)**

```bash
brew install git python node pandoc poppler tesseract
brew install --cask libreoffice
python3 -m pip install -r requirements.txt
npm install
```

En macOS, LibreOffice queda en `/Applications/LibreOffice.app` y el comando
`soffice` puede no estar en el `PATH`; agregalo si el verificador lo marca:

```bash
export PATH="/Applications/LibreOffice.app/Contents/MacOS:$PATH"
```

## Verificación en detalle

```powershell
python herramientas/scripts/verificar_entorno.py
```

Comprueba dos grupos:

- **Base**: Python 3.10+ y `git`. Siempre obligatorios.
- **Por formato**: lo que necesita `.docx`, `.xlsx`, `.pdf` y `.md`.

Opciones:

| Comando | Qué exige |
| --- | --- |
| `verificar_entorno.py` | Sólo la base. Informa el estado de cada formato. |
| `verificar_entorno.py --formato docx` | Base + todo lo de Word. Falla si falta algo. |
| `verificar_entorno.py --strict` | Todo lo de todos los formatos. Falla si falta algo. |
| `verificar_entorno.py --json` | Igual, en JSON, para scripts. |

Códigos de salida: `0` no falta nada obligatorio, `1` falta algo.

La salida separa tres cosas que conviene no confundir:

```text
Formatos listos: markdown
Formatos incompletos: docx, xlsx, pdf
Resultado: base lista — podés generar lo que esté en 'Formatos listos'.
```

Eso significa que el repositorio funciona y que podés generar `.md`, pero que
todavía no hay con qué armar un `.docx`. No es un error: es un inventario.

## Dependencias por formato

| Formato | Necesita |
| --- | --- |
| `.md` | nada más que Python |
| `.docx` | Node.js, npm, `docx` (npm), Pandoc, LibreOffice, Poppler, `defusedxml`, `lxml`, `validators`, Pillow |
| `.xlsx` | LibreOffice, `openpyxl`, `pandas` |
| `.pdf` | Poppler, `pypdf`, `pdfplumber`, `reportlab`, `pdf2image`, Pillow |
| PDF escaneado | además Tesseract y `pytesseract` (no instalados por defecto) |

Los opcionales no están en `requirements.txt`: `pytesseract` y `markitdown` se
instalan a mano sólo si hacen falta. El verificador los informa aparte y nunca
bloquean.

Los scripts de `herramientas/scripts/` **no aparecen en esa tabla** porque no
necesitan nada: usan sólo la biblioteca estándar de Python.

## Puesta en marcha del repositorio

Con el entorno listo, falta preparar tu zona de trabajo:

```powershell
python herramientas/scripts/init_local.py
```

Crea las carpetas de `usuario/` y copia cada contrato de
`herramientas/contratos/` a su archivo real en `usuario/datos/`. Sólo si el
archivo **no existe**: nunca sobrescribe nada tuyo, y podés correrlo las veces
que quieras.

Después:

1. Completá los `PENDIENTE` de `usuario/datos/` — eso lo hacés vos, no el
   agente.
2. Validá:

```powershell
python herramientas/scripts/validar_datos.py
python herramientas/scripts/validar_datos.py --estricto
```

`--estricto` devuelve `1` mientras quede algún `PENDIENTE`. Cuando devuelva
`0`, la fuente de datos está completa y se puede generar documentos.

## Problemas comunes

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `soffice` no se encuentra | LibreOffice no está en el `PATH` | Agregá `C:\Program Files\LibreOffice\program`. El verificador también lo busca ahí. |
| `pdftoppm` no se encuentra | Poppler instalado pero fuera del `PATH` | Buscá `pdftoppm.exe` y agregá su carpeta al `PATH`. |
| `pandoc: command not found` | No está instalado o falta reabrir la terminal | `winget install JohnMacFarlane.Pandoc`, reabrí PowerShell. |
| `Cannot find module 'docx'` | El script generador está fuera del repositorio; el `npm install` no lo alcanza | Mové el script dentro del repositorio, o definí `NODE_PATH` apuntando a `node_modules`. |
| `no matching distribution found` al instalar `pandas` | La versión de Python es más nueva que los binarios disponibles | Creá un venv con `py -3.12 -m venv .venv`. |
| `pip` no se reconoce | Python no está en el `PATH` | Reabrí la terminal; si sigue, reinstalá marcando «Add Python to PATH». |
| Excel muestra fórmulas en vez de valores | No se recalculó el libro | Necesitás LibreOffice: la skill lo usa para calcular sobre una copia. |
| `PermissionError` al abrir un archivo generado | El archivo está abierto en Word/Excel | Cerrá el archivo y volvé a generar. |
| Aparece `LibreOffice 26.x` y `Press Enter to continue...` | Alguien ejecutó `soffice --version` a mano: el lanzador de consola imprime la versión y espera un Enter | Apretá Enter. No es un error. El verificador ya no ejecuta LibreOffice: sólo comprueba que exista. |
| Instalé algo y el verificador dice que falta | La ventana abierta tiene el `PATH` viejo | Ya está resuelto: ambos scripts releen el `PATH` del registro. Si ves esto, es un bug: reportalo. |

## Qué NO hace falta instalar

- **Dependencias para los scripts del repositorio.** `init_local.py`,
  `validar_datos.py`, `nuevo_entregable.py`, `verificar_limites.py`,
  `verificar_entorno.py` e `instalar_todo.py` usan sólo la biblioteca estándar de
  Python 3.10+. Funcionan con `pip` vacío.
- **`python-docx`.** No se usa, ver la aclaración de arriba.
- **Microsoft Word o Excel.** Qué programa de oficina uses es indiferente: LibreOffice
  se instala sólo para las conversiones y no reemplaza nada.
- **Una base de datos, Docker o un servidor.** Todo es local.
- **Conexión a internet**, después de instalar. Nada del flujo consulta la red.

## Resumen

Para usuario no técnico, un solo comando:

```text
python herramientas/scripts/instalar_todo.py
```

Detalle técnico:

```text
Base obligatoria:      Python 3.10+  ·  git
Python:                pip install -r requirements.txt
Node:                  npm install
Programas del sistema: Pandoc  ·  LibreOffice  ·  Poppler  (+ Tesseract opcional)
Verificar:             python herramientas/scripts/verificar_entorno.py
Instalar lo que falta: python herramientas/scripts/instalar_todo.py --si
Preparar tu zona:      python herramientas/scripts/init_local.py
```
