# Tipos de documento

Catálogo de los documentos administrativos que este repositorio produce. Cada tipo
declara qué datos de `usuario/datos/` son obligatorios y qué skill se usa para generarlo.
Si falta un dato obligatorio, el agente **pregunta**; no redacta con supuestos.

| `tipo` | Para qué sirve | Skill | Datos obligatorios | Salida típica |
| --- | --- | --- | --- | --- |
| `memorandum` | Comunicación interna formal entre áreas o hacia el personal | `internal-comms` + `docx` | `entidad`, `firmantes`, `contactos` | `.docx`, `.md` |
| `circular` | Aviso de alcance general a todo el personal | `internal-comms` + `docx` | `entidad`, `firmantes` | `.docx`, `.md` |
| `informe` | Resultados, gestión o incidencias de un periodo | `internal-comms` + `docx` | `entidad`, `firmantes`, tabla de sustento | `.docx`, `.pdf` |
| `oficio` | Comunicación hacia una entidad externa | `internal-comms` + `docx` | `entidad`, `firmantes` | `.docx`, `.pdf` |
| `solicitud` | Petición formal dirigida a una autoridad o entidad | `internal-comms` + `docx` | `entidad`, `firmantes` | `.docx`, `.pdf` |
| `constancia` | Certifica un hecho verificable (atención, trabajo, permanencia) | `docx` | `entidad`, `firmantes` | `.docx`, `.pdf` |
| `acta` | Registro de una reunión con acuerdos y responsables | `internal-comms` + `docx` | `entidad`, `contactos` | `.docx`, `.md` |
| `reporte` | Consolidado de datos con tablas y totales | `xlsx` | `servicios`, `tarifas`, `horarios` | `.xlsx`, `.pdf` |
| `cotizacion` | Propuesta económica de servicios | `xlsx` o `docx` | `entidad`, `servicios`, `tarifas` | `.xlsx`, `.docx` |
| `comunicado` | Mensaje de difusión pública | `internal-comms` + `docx` | `entidad` | `.docx`, `.md` |

`entidad` = `usuario/datos/organizacion/entidad.csv` · `contactos` =
`usuario/datos/organizacion/contactos.csv` · `firmantes` =
`usuario/datos/organizacion/firmantes.csv` · `servicios`/`tarifas`/`horarios` =
`usuario/datos/tablas/`

## Formato de salida

| Extensión | Cuándo | Skill |
| --- | --- | --- |
| `.md` | Borrador rápido, revisión de contenido, documentación interna, versionado en texto | ninguna (escritura directa) |
| `.docx` | Documento formal con membrete, firma y formato institucional | `docx` |
| `.pdf` | Versión final inmutable para envío o archivo | `pdf` (o conversión desde `.docx`) |
| `.xlsx` | Tablas, tarifas, reportes con fórmulas y totales | `xlsx` |

Regla práctica: si el usuario no especifica formato, entregá `.docx` para documentos
formales y `.md` para contenido que va a seguir iterando. Si pide "Excel", es `.xlsx`,
nunca `.csv`.

## Esqueletos de secciones

### `memorandum`

```text
1. Encabezado      — logo, razón social, RUC, dirección
2. Título          — MEMORÁNDUM N.º <correlativo>-<año>-<área>
3. Destinatario    — nombre, cargo, área (de contactos.csv)
4. Remitente       — nombre, cargo (de firmantes.csv)
5. Asunto          — una línea, concreta
6. Fecha           — AAAA-MM-DD o "Puno, 25 de noviembre de 2026"
7. Cuerpo          — contexto → decisión → alcance → plazos
8. Cierre          — "Atentamente," + firma + sello
9. Copia           — opcional, destinatarios en copia
```

### `circular`

```text
1. Encabezado institucional
2. Título          — CIRCULAR N.º <correlativo>-<año>
3. Dirigida a      — "Todo el personal" / área específica
4. Asunto
5. Cuerpo          — disposición, vigencia, responsables de cumplimiento
6. Fecha y firma   — gerencia o dirección
```

### `informe`

```text
1. Encabezado institucional
2. Título          — INFORME N.º <correlativo>-<año>-<área>
3. Destinatario
4. Asunto          — "Informe de <materia> correspondiente al periodo <periodo>"
5. I.   Antecedentes
6. II.  Objetivos
7. III. Actividades realizadas (tabla con datos de sustento)
8. IV.  Resultados (cifras de servicios/tarifas/horarios)
9. V.   Conclusiones
10. VI. Recomendaciones
11. Fecha y firma
```

### `acta`

```text
1. Título          — ACTA DE REUNIÓN N.º <correlativo>-<año>
2. Fecha, hora, lugar
3. Asistentes      — nombre y cargo (de contactos.csv)
4. Agenda          — puntos numerados
5. Desarrollo      — por cada punto: lo tratado y lo decidido
6. Acuerdos        — tabla: acuerdo | responsable | plazo
7. Cierre          — firma de los asistentes
```

### `reporte`

```text
Hoja 1 "Resumen"   — periodo, totales, indicadores
Hoja 2 "Detalle"   — filas por servicio/área con fórmulas de total
Hoja 3 "Notas"     — fuente de los datos y fecha de corte
```

### `cotizacion`

```text
1. Encabezado      — datos de la entidad
2. Datos del cliente
3. Título          — COTIZACIÓN N.º <correlativo>-<año>
4. Tabla           — código, servicio, cantidad, precio unitario, subtotal
5. Totales         — subtotal, IGV si corresponde, total
6. Condiciones     — vigencia, forma de pago, plazo de atención
7. Fecha y firma
```

## Reglas transversales

1. **Numeración de correlativos**: si el usuario no aporta el número, dejá
   `<correlativo>` como marcador visible y pedilo antes de la entrega final.
2. **Firmas**: sólo firma quien figura en `firmantes.csv` con un `alcance` que
   incluya el tipo de documento. Si no hay firmante válido, no inventes uno.
3. **Fechas**: siempre en `AAAA-MM-DD` en los datos; en el cuerpo del documento se
   puede escribir en texto ("25 de noviembre de 2026") respetando el estilo pedido.
4. **Cifras**: todo monto o cantidad debe poder rastrearse a `usuario/datos/tablas/`. Si el
   número no está en la fuente, no va en el documento.
5. **Tono**: formal, impersonal y sobrio en documentos oficiales; cercano y directo
   sólo en comunicados internos donde el usuario lo pida.
