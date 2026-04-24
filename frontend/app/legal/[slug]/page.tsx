import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { Shell } from "@/app/components/layout/shell";
import { Badge } from "@/app/components/primitives/shared";
import { findPublicLegalDoc, getPublicLegalDocContent } from "../legal-loader";

type Params = { slug: string };

function renderMarkdownish(content: string) {
  const lines = content.split(/\r?\n/);
  const nodes: ReactNode[] = [];
  let bullets: string[] = [];

  const flushBullets = (key: string) => {
    if (!bullets.length) return;
    nodes.push(
      <ul key={key} className="list-disc space-y-2 pl-6 text-sm leading-7 text-[color:var(--text-secondary)]">
        {bullets.map((item, index) => <li key={`${key}-${index}`}>{item}</li>)}
      </ul>
    );
    bullets = [];
  };

  lines.forEach((rawLine, index) => {
    const line = rawLine.trimEnd();
    const key = `line-${index}`;
    if (!line.trim()) {
      flushBullets(`bullets-${index}`);
      return;
    }
    if (line.startsWith("# ")) {
      flushBullets(`bullets-${index}`);
      return;
    }
    if (line.startsWith("## ")) {
      flushBullets(`bullets-${index}`);
      nodes.push(
        <h2 key={key} className="mt-8 text-xl font-semibold tracking-[-0.03em] text-[color:var(--text-primary)]">
          {line.slice(3)}
        </h2>
      );
      return;
    }
    if (line.startsWith("- ")) {
      bullets.push(line.slice(2));
      return;
    }
    flushBullets(`bullets-${index}`);
    nodes.push(
      <p key={key} className="whitespace-pre-wrap text-sm leading-7 text-[color:var(--text-secondary)]">
        {line}
      </p>
    );
  });

  flushBullets("bullets-end");
  return nodes;
}

export default async function LegalDocumentPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const doc = findPublicLegalDoc(slug);
  if (!doc) notFound();
  const content = await getPublicLegalDocContent(doc.filename);

  return (
    <Shell
      title={doc.title}
      subtitle={doc.summary}
      action={<Link href="/legal" className="secondary-btn">Volver al centro legal</Link>}
    >
      <div className="flex flex-wrap gap-2">
        <Badge tone="sky">{doc.category}</Badge>
        <Badge tone="slate">{doc.audience}</Badge>
        <Badge tone="gold">Slug: {doc.slug}</Badge>
      </div>
      <article className="mt-6 space-y-4 rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-6">
        {renderMarkdownish(content)}
      </article>
    </Shell>
  );
}
