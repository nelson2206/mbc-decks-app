'use client';
import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Sparkles, AlertTriangle, CheckCircle, Loader2, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { AuthGuard } from '@/components/AuthGuard';
import { decks, generateApi, auditApi } from '@/lib/api';

function ReviewInner() {
  const params = useSearchParams();
  const router = useRouter();
  const deckId = params.get('deckId') || '';
  const [deck, setDeck] = useState<any>(null);
  const [polling, setPolling] = useState(false);

  const refreshDeck = async () => {
    if (!deckId) return;
    const d = await decks.get(deckId);
    setDeck(d);
    return d;
  };

  useEffect(() => {
    refreshDeck();
  }, [deckId]);

  // Poll deck status while pipeline runs
  useEffect(() => {
    if (!deck) return;
    const inProgress = ['generating', 'researching', 'structuring', 'writing', 'visual', 'audit'].includes(deck.status);
    if (!inProgress) {
      setPolling(false);
      return;
    }
    setPolling(true);
    const id = setInterval(refreshDeck, 5000);
    return () => clearInterval(id);
  }, [deck?.status]);

  const handleGenerate = async () => {
    await generateApi.start(deckId);
    refreshDeck();
  };

  const handleReAudit = async () => {
    await auditApi.run(deckId);
    refreshDeck();
  };

  if (!deck) return <div className="text-stone-500">Cargando…</div>;

  const blocked = deck.audit_status === 'BLOCKED';
  const ready = deck.status === 'ready';

  return (
    <AuthGuard>
      <div className="max-w-4xl">
        <h1 className="text-3xl font-bold text-pruno mb-2">{deck.title}</h1>
        <p className="text-stone-600 mb-8">Cliente: {deck.client_name} · Tema: {deck.topic} · Estado: <strong>{deck.status}</strong></p>

        {/* Action card */}
        <div className="card mb-6">
          <h2 className="font-semibold text-pruno mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-magenta" /> Pipeline multi-agente
          </h2>
          {deck.status === 'interviewing_done' && (
            <button onClick={handleGenerate} className="btn-magenta inline-flex items-center gap-2">
              <Sparkles className="w-4 h-4" /> Iniciar generación con IA
            </button>
          )}
          {polling && (
            <div className="flex items-center gap-2 text-amazonico">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>El pipeline está corriendo… (puede tomar 2-5 minutos)</span>
            </div>
          )}
          {ready && (
            <div className="flex items-center justify-between bg-verde/10 p-4 rounded-chamfer">
              <div className="flex items-center gap-2 text-verde">
                <CheckCircle className="w-5 h-5" />
                <span className="font-semibold">Deck listo</span>
              </div>
              <a href={decks.download(deck.id)} target="_blank" className="btn-primary inline-flex items-center gap-2">
                <Download className="w-4 h-4" /> Descargar .pptx
              </a>
            </div>
          )}
        </div>

        {/* Audit report */}
        {deck.audit_report && Object.keys(deck.audit_report).length > 0 && (
          <div className="card mb-6">
            <h2 className="font-semibold text-pruno mb-4 flex items-center gap-2">
              {blocked
                ? <AlertTriangle className="w-5 h-5 text-magenta" />
                : <CheckCircle className="w-5 h-5 text-verde" />}
              Auditoría visual A9 — {deck.audit_status}
            </h2>
            {deck.audit_report.summary && (
              <div className="grid grid-cols-4 gap-4 mb-4">
                <Stat label="Críticos" value={deck.audit_report.summary.critical} color="text-magenta" />
                <Stat label="Warnings" value={deck.audit_report.summary.warning} color="text-naranja" />
                <Stat label="Neutrales" value={deck.audit_report.summary.neutral} color="text-stone-600" />
                <Stat label="Aprobados" value={deck.audit_report.summary.approved} color="text-verde" />
              </div>
            )}
            {blocked && (
              <div className="bg-magenta/10 p-4 rounded-chamfer">
                <p className="font-semibold text-magenta mb-2">El deck NO se puede entregar</p>
                <p className="text-sm text-stone-700">Hay branding hostil detectado. Revisa los hallazgos y aplica los reemplazos antes de re-auditar.</p>
                <button onClick={handleReAudit} className="btn-primary mt-3">Re-auditar</button>
              </div>
            )}
            {deck.audit_report.findings?.filter((f: any) => f.severity === 'CRITICAL').slice(0, 5).map((f: any) => (
              <div key={f.image_id} className="border-l-4 border-magenta pl-3 my-3">
                <div className="text-sm font-semibold text-pruno">{f.image_id} (slides {f.appears_in_slides.join(', ')})</div>
                <div className="text-xs text-stone-600">{f.description}</div>
              </div>
            ))}
          </div>
        )}

        {/* Reviews del Manager y Socios */}
        {deck.review_consolidated && (
          <div className="card">
            <h2 className="font-semibold text-pruno mb-4">Revisión Manager + Socios</h2>
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{deck.review_consolidated}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="text-center bg-ceramica/40 p-3 rounded-chamfer">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-stone-600">{label}</div>
    </div>
  );
}

export default function ReviewPage() {
  return <Suspense fallback={null}><ReviewInner /></Suspense>;
}
