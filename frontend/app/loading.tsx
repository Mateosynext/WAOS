export default function Loading() {
  return (
    <main className="min-h-screen bg-[var(--client-shell-bg)] px-4 py-8 text-[color:var(--text-primary)]">
      <div className="mx-auto max-w-5xl space-y-4">
        <div className="panel animate-pulse p-6">
          <div className="h-4 w-40 rounded-full bg-[color:var(--surface-muted)]" />
          <div className="mt-4 h-10 w-2/3 rounded-2xl bg-[color:var(--surface-muted)]" />
          <div className="mt-3 h-4 w-full rounded-full bg-[color:var(--surface-muted)]" />
          <div className="mt-2 h-4 w-4/5 rounded-full bg-[color:var(--surface-muted)]" />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="panel animate-pulse p-6">
              <div className="h-4 w-24 rounded-full bg-[color:var(--surface-muted)]" />
              <div className="mt-4 h-10 w-20 rounded-2xl bg-[color:var(--surface-muted)]" />
              <div className="mt-4 h-4 w-full rounded-full bg-[color:var(--surface-muted)]" />
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
