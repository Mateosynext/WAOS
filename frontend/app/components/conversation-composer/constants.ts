import type { ComposerMode } from "./types";

export const QUICK_REPLIES = [
  "Hola, ya estoy revisando tu caso y te respondo con claridad en un momento.",
  "Gracias por escribir. ¿Me confirmas el pedido, cita o tema exacto para ayudarte más rápido?",
  "Ya tomé este caso manualmente. Te acompaño por aquí hasta cerrarlo.",
  "Entendido. Voy a verificarlo y te comparto el siguiente paso hoy mismo.",
];

export const SNIPPETS = [
  { label: "Seguimiento", value: "Dame unos minutos para revisarlo y te confirmo por aquí el siguiente paso." },
  { label: "Agendar", value: "¿Qué horario te funciona mejor? Te comparto opciones en cuanto me confirmes." },
  { label: "Cobro", value: "Voy a revisar el estatus del cobro y te actualizo con la referencia exacta." },
];

export const MODE_LABELS: Array<{ value: ComposerMode; label: string; hint: string }> = [
  { value: "text", label: "Texto", hint: "Respuesta clásica" },
  { value: "note", label: "Nota interna", hint: "No sale al cliente" },
  { value: "image", label: "Imagen", hint: "Link o media ID" },
  { value: "audio", label: "Audio", hint: "Nota o clip" },
  { value: "document", label: "Documento", hint: "PDF, DOC, XLS" },
  { value: "video", label: "Video", hint: "Media saliente" },
  { value: "template", label: "Template", hint: "Plantilla aprobada" },
  { value: "interactive_button", label: "Botones", hint: "Reply buttons" },
  { value: "interactive_list", label: "Lista", hint: "Menú interactivo" },
  { value: "flow_entrypoint", label: "Flow", hint: "Entrypoint de Flow" },
  { value: "product", label: "Producto", hint: "Single product" },
  { value: "catalog", label: "Catálogo", hint: "Multi-product" },
  { value: "mark_as_read", label: "Marcar leído", hint: "Status técnico" },
];
