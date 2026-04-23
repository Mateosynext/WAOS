export type ComposerMode =
  | "text"
  | "note"
  | "image"
  | "audio"
  | "document"
  | "video"
  | "template"
  | "interactive_button"
  | "interactive_list"
  | "flow_entrypoint"
  | "product"
  | "catalog"
  | "mark_as_read";

export type ButtonDraft = { id: string; title: string };
export type ListRowDraft = { section: string; id: string; title: string; description: string };

export type ComposerResult = {
  kind: "text" | "note";
  body: string;
  whatsappPayload?: Record<string, unknown>;
  errors: string[];
};
