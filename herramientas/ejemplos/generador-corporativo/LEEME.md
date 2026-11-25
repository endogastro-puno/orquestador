# Ejemplo: generador propio del usuario

Esta carpeta es un **ejemplo** que vive en el proyecto. El código del
generador de verdad vive en `usuario/generadores/`, que es zona del usuario.

## Cómo usarlo

1. Copiá la carpeta a tu zona:

   ```bash
   python -c "import shutil; shutil.copytree('herramientas/ejemplos/generador-corporativo', 'usuario/generadores/corporativo')"
   ```

2. Abrí `usuario/generadores/corporativo/generador.json` y ajustá `nombre` y
   `tipos`. Con `"tipos": ["*"]` el generador se aplica a **todos** los tipos de
   documento; con `"tipos": ["informe", "manual"]` sólo a esos.

3. Instalá la dependencia del ejemplo (si vas a usar Python):

   ```bash
   python -m pip install python-docx
   ```

4. Comprobá que el motor lo detecta:

   ```bash
   python herramientas/scripts/listar_generadores.py
   ```

5. Generá un documento:

   ```bash
   python herramientas/scripts/generar_documento.py --tipo manual
   ```

Para volver atrás y usar el renderizador genérico:

```bash
python herramientas/scripts/generar_documento.py --tipo manual --sin-generador
```

## Qué muestra el ejemplo

- El motor resuelve el contenido (placeholders, tablas, `PENDIENTE`) y se lo
  entrega ya resuelto en `payload["bloques"]`.
- El generador aplica **sólo formato**: tipografía, color de títulos, membrete
  con logo, pie con número de página.
- El generador escribe el archivo en `payload["salida"]` y termina con código 0.
- Si el documento final tuviera un `PENDIENTE`, el generador falla en vez de
  entregarlo.

El contrato completo está en `herramientas/docs/contrato-generador.md`.
