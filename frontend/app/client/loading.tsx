function PortalLoadingShell() {
  return (
    <main id="main-content" className="min-h-screen bg-[var(--client-shell-bg)] text-[color:var(--text-primary)]">
      <div className="mx-auto max-w-[1440px] px-4 pb-8 pt-[max(1rem,env(safe-area-inset-top))] sm:px-6 lg:px-8">
        <div className="rounded-[34px] border border-[color:var(--border-soft)] bg-[color:var(--surface-elevated)] p-4 shadow-[var(--shadow-xl)] sm:p-6 lg:p-8">
          <div className="animate-pulse space-y-6">
            <div className="h-5 w-36 rounded-full bg-[color:var(--surface-muted)]" />
            <div className="h-12 w-3/4 rounded-[20px] bg-[color:var(--surface-muted)]" />
            <div className="h-6 w-full max-w-3xl rounded-[16px] bg-[color:var(--surface-muted)]" />
            <div className="flex gap-2 overflow-hidden rounded-[24px] border border-[color:var(--border-soft)] p-2">
              {Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-10 w-28 rounded-full bg-[color:var(--surface-muted)]" />)}
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-40 rounded-[28px] bg-[color:var(--surface-muted)]" />)}
            </div>
            <div className="grid gap-4 xl:grid-cols-3">
              {Array.from({ length: 3 }).map((_, index) => <div key={index} className="h-52 rounded-[28px] bg-[color:var(--surface-muted)]" />)}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function Loading() {
  return <PortalLoadingShell />;
}
