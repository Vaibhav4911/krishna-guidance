export default function ApiOverviewPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-6 py-12">
      <div className="rounded-[28px] border border-slate-200 bg-white p-8 shadow-soft">
        <div className="text-sm uppercase tracking-[0.25em] text-slate-500">API Overview</div>
        <h1 className="mt-4 text-3xl font-semibold text-slate-900">Krishna Guidance service endpoints</h1>

        <div className="mt-8 space-y-4 text-sm text-slate-600">
          <div className="rounded-2xl bg-slate-50 p-4">
            <div className="font-mono text-base text-night">GET /health/live</div>
            <p className="mt-2">Returns a simple liveness check for the API service.</p>
          </div>
          <div className="rounded-2xl bg-slate-50 p-4">
            <div className="font-mono text-base text-night">GET /health/ready</div>
            <p className="mt-2">Returns service readiness metadata and dependency state.</p>
          </div>
          <div className="rounded-2xl bg-slate-50 p-4">
            <div className="font-mono text-base text-night">POST /api/v1/chat/message</div>
            <p className="mt-2">Accepts a user message and returns a structured answer with citations and safety metadata.</p>
          </div>
        </div>
      </div>
    </main>
  );
}
