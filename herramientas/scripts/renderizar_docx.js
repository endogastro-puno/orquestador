// Renderizador genérico de DOCX para el motor declarativo.
// Lee un payload JSON producido por generar_documento.py. No contiene datos de empresa.
//
// Uso: node renderizar_docx.js <payload.json> <salida.docx>

const fs = require("fs");
const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  PageBreak,
  Table,
  TableRow,
  TableCell,
  WidthType,
  BorderStyle,
  ShadingType,
  Footer,
  PageNumber,
  VerticalAlign,
} = require("docx");

const ANCHO = 9026; // A4 (11906) menos márgenes de 1440 por lado
const AZUL = "1F3864";
const AZUL_CLARO = "D9E2F3";
const GRIS = "F2F2F2";
const FUENTE = "Arial";

const SIN_BORDES = {
  top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  insideHorizontal: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  insideVertical: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
};

const BORDES_FINOS = {
  top: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" },
  bottom: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" },
  left: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" },
  right: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" },
  insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" },
  insideVertical: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" },
};

function celda(texto, opciones = {}) {
  return new TableCell({
    width: { size: opciones.ancho ?? 3000, type: WidthType.DXA },
    shading: opciones.fondo
      ? { type: ShadingType.CLEAR, fill: opciones.fondo, color: "auto" }
      : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 120, right: 120 },
    children: [
      new Paragraph({
        alignment: opciones.alineacion,
        spacing: { before: 0, after: 0, line: 240 },
        children: [
          new TextRun({
            text: String(texto ?? ""),
            font: FUENTE,
            size: opciones.tamano ?? 20,
            bold: opciones.negrita ?? false,
            color: opciones.color,
          }),
        ],
      }),
    ],
  });
}

function tabla(encabezado, filas, anchos, opciones = {}) {
  const anchosValidos = anchos && anchos.length === encabezado.length ? anchos : null;
  const anchosFinales = anchosValidos ?? encabezado.map(() => Math.floor(ANCHO / encabezado.length));
  return new Table({
    columnWidths: anchosFinales,
    borders: opciones.sinBordes ? SIN_BORDES : BORDES_FINOS,
    rows: [
      new TableRow({
        tableHeader: true,
        children: encabezado.map((valor, i) =>
          celda(valor, {
            ancho: anchosFinales[i],
            negrita: true,
            fondo: opciones.encabezadoAzul ? AZUL_CLARO : undefined,
          })
        ),
      }),
      ...filas.map(
        (fila) =>
          new TableRow({
            children: encabezado.map((_, i) =>
              celda(fila[i] ?? "", {
                ancho: anchosFinales[i],
                negrita: opciones.primeraNegrita && i === 0,
                fondo: opciones.franjas && filas.indexOf(fila) % 2 === 1 ? GRIS : undefined,
              })
            ),
          })
      ),
    ],
  });
}

function parrafo(texto, opciones = {}) {
  return new Paragraph({
    alignment: opciones.alineacion,
    spacing: {
      before: opciones.antes ?? 0,
      after: opciones.despues ?? 120,
      line: 276,
    },
    children: [
      new TextRun({
        text: String(texto ?? ""),
        font: FUENTE,
        size: opciones.tamano ?? 22,
        bold: opciones.negrita ?? false,
        italics: opciones.cursiva ?? false,
        color: opciones.color,
      }),
    ],
  });
}

function titulo(texto, nivel) {
  // El tamaño, la negrita y el color viven sólo en styles.default.*; repetirlos
  // acá crea dos fuentes de verdad que pueden divergir.
  const niveles = {
    1: HeadingLevel.HEADING_1,
    2: HeadingLevel.HEADING_2,
    3: HeadingLevel.HEADING_3,
  };
  return new Paragraph({
    heading: niveles[nivel] ?? HeadingLevel.HEADING_2,
    children: [new TextRun({ text: String(texto) })],
  });
}

function lista(items, numerada) {
  return items.map(
    (item, i) =>
      new Paragraph({
        spacing: { after: 100, line: 276 },
        indent: { left: 480, hanging: 480 },
        children: [
          new TextRun({
            text: numerada ? `${i + 1}. ${item}` : `•  ${item}`,
            font: FUENTE,
            size: 22,
          }),
        ],
      })
  );
}

function renderizar(bloque, payload) {
  switch (bloque.tipo) {
    case "pagina":
      return [new Paragraph({ children: [new PageBreak()] })];

    case "portada":
      return (bloque.lineas ?? []).map((linea) =>
        parrafo(linea.texto, {
          alineacion: AlignmentType.CENTER,
          tamano: linea.tamano ?? 22,
          negrita: linea.negrita,
          cursiva: linea.cursiva,
          color: linea.color,
          despues: linea.espacio_despues ?? 120,
        })
      );

    case "titulo":
      return [titulo(bloque.texto, bloque.nivel ?? 1)];

    case "parrafo":
      return [
        parrafo(bloque.texto, {
          cursiva: bloque.cursiva,
          tamano: bloque.tamano,
        }),
      ];

    case "lista":
    case "numerada":
      return lista(bloque.items ?? [], bloque.tipo === "numerada" || bloque.numerada === true);

    case "tabla":
      return [
        tabla(bloque.encabezado ?? [], bloque.filas ?? [], bloque.anchos, {
          encabezadoAzul: bloque.encabezado_azul === true,
          primeraNegrita: bloque.primera_negrita === true,
        }),
        parrafo(""),
      ];

    case "indice": {
      const anchoPagina = 1526;
      return [
        tabla(
          ["Sección", "Página"],
          (payload.indice ?? []).map((entrada) => [entrada.texto, String(entrada.pagina)]),
          [ANCHO - anchoPagina, anchoPagina],
          { encabezadoAzul: true }
        ),
      ];
    }

    case "firma":
      return [
        parrafo(""),
        parrafo(""),
        parrafo("_______________________________________", {
          alineacion: AlignmentType.CENTER,
          despues: 40,
        }),
        parrafo(bloque.cargo, { alineacion: AlignmentType.CENTER, negrita: true, despues: 20 }),
        parrafo(bloque.entidad, { alineacion: AlignmentType.CENTER, despues: 20 }),
        parrafo(bloque.texto, { alineacion: AlignmentType.CENTER, tamano: 20 }),
      ];

    default:
      throw new Error(`bloque desconocido: ${bloque.tipo}`);
  }
}

function construir(payload) {
  const children = (payload.bloques ?? []).flatMap((bloque) => renderizar(bloque, payload));
  return new Document({
    creator: payload.titulo ?? "Documento generado",
    title: payload.titulo ?? "Documento generado",
    description: payload.pie ?? "",
    styles: {
      default: {
        document: {
          run: { font: FUENTE, size: 22 },
          paragraph: { spacing: { after: 120, line: 276 } },
        },
        heading1: {
          run: { font: FUENTE, size: 28, bold: true, color: AZUL },
          paragraph: { spacing: { before: 320, after: 180 }, keepNext: true },
        },
        heading2: {
          run: { font: FUENTE, size: 24, bold: true, color: AZUL },
          paragraph: { spacing: { before: 280, after: 140 }, keepNext: true },
        },
        heading3: {
          run: { font: FUENTE, size: 22, bold: true, color: "333333" },
          paragraph: { spacing: { before: 200, after: 100 }, keepNext: true },
        },
      },
    },
    sections: [
      {
        properties: {
          page: {
            size: { width: 11906, height: 16838 },
            margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
          },
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 0, after: 0 },
                children: [
                  new TextRun({
                    text: `${payload.pie ?? ""} · Página `,
                    font: FUENTE,
                    size: 16,
                    color: "808080",
                  }),
                  new TextRun({
                    children: [PageNumber.CURRENT],
                    font: FUENTE,
                    size: 16,
                    color: "808080",
                  }),
                  new TextRun({ text: " de ", font: FUENTE, size: 16, color: "808080" }),
                  new TextRun({
                    children: [PageNumber.TOTAL_PAGES],
                    font: FUENTE,
                    size: 16,
                    color: "808080",
                  }),
                ],
              }),
            ],
          }),
        },
        children,
      },
    ],
  });
}

const [, , rutaPayload, rutaSalida] = process.argv;
if (!rutaPayload || !rutaSalida) {
  console.error("Uso: node renderizar_docx.js <payload.json> <salida.docx>");
  process.exit(1);
}

let payload;
try {
  payload = JSON.parse(fs.readFileSync(rutaPayload, "utf8"));
} catch (error) {
  console.error(`Payload inválido: ${error.message}`);
  process.exit(1);
}

Packer.toBuffer(construir(payload))
  .then((buffer) => {
    fs.writeFileSync(rutaSalida, buffer);
    console.log(`OK ${rutaSalida} ${buffer.length} bytes`);
  })
  .catch((error) => {
    console.error(`FALLO: ${error.message}`);
    process.exit(1);
  });
