import { publicLegalContent } from "./legal-content";
import { publicLegalDocs } from "./legal-registry";

export async function getPublicLegalDocContent(filename: string) {
  const match = publicLegalDocs.find((item) => item.filename === filename);
  if (!match) throw new Error(`Documento legal no encontrado: ${filename}`);
  return publicLegalContent[match.slug] || "";
}

export function findPublicLegalDoc(slug: string) {
  return publicLegalDocs.find((item) => item.slug === slug) || null;
}
