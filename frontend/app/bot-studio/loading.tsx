export default function Loading() {
  return (
    <main className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-8 sm:px-6 lg:px-8" aria-busy="true" aria-label="Cargando Bot Studio">
      <section className="rounded-[32px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-6 shadow-[var(--shadow-sm)]">
        <div className="h-3 w-32 animate-pulse rounded-full bg-[color:var(--surface-subtle)]" />
        <div className="mt-4 h-8 w-72 animate-pulse rounded-full bg-[color:var(--surface-subtle)]" />
        <p className="mt-4 max-w-2xl text-sm leading-6 text-[color:var(--text-secondary)]">Preparando el paso activo del wizard y sus datos necesarios.</p>
      </section>
      <section className="grid gap-4 md:grid-cols-3">
        <div className="h-28 animate-pulse rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)]" />
        <div className="h-28 animate-pulse rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)]" />
        <div className="h-28 animate-pulse rounded-[24px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)]" />
      </section>
      <section className="rounded-[28px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-5">
        <div className="h-5 w-48 animate-pulse rounded-full bg-[color:var(--surface-subtle)]" />
        <div className="mt-5 grid gap-3">
          <div className="h-12 animate-pulse rounded-2xl bg-[color:var(--surface-subtle)]" />
          <div className="h-12 animate-pulse rounded-2xl bg-[color:var(--surface-subtle)]" />
          <div className="h-12 animate-pulse rounded-2xl bg-[color:var(--surface-subtle)]" />
        </div>
      </section>
    </main>
  );
}
