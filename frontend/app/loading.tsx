export default function Loading() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.12),_transparent_24%),linear-gradient(180deg,#07111f_0%,#0b1220_100%)] px-4 py-8 text-slate-50">
      <div className="mx-auto max-w-5xl space-y-4">
        <div className="panel animate-pulse p-6">
          <div className="h-4 w-40 rounded-full bg-white/10" />
          <div className="mt-4 h-10 w-2/3 rounded-2xl bg-white/10" />
          <div className="mt-3 h-4 w-full rounded-full bg-white/10" />
          <div className="mt-2 h-4 w-4/5 rounded-full bg-white/10" />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="panel animate-pulse p-6">
              <div className="h-4 w-24 rounded-full bg-white/10" />
              <div className="mt-4 h-10 w-20 rounded-2xl bg-white/10" />
              <div className="mt-4 h-4 w-full rounded-full bg-white/10" />
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
