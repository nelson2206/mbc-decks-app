'use client';
import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Sparkles, AlertTriangle, CheckCircle, Loader2, Download, RotateCw, XCircle, StopCircle, Ban } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { AuthGuard } from '@/components/AuthGuard';
import { decks, generateApi, auditApi } from '@/lib/api';

const PIPELINE_STEPS = [
  { key: 'researching',  label: '🔬 A2 Investigador',     pct: 10 },
  { key: 'structuring',  label: '🏗️ A3 Estructurador',    pct: 25 },
  { key: 'writing',      label: '✍️ A4 Contenido',        pct: 50 },
  { key: 'visual',       label: '🎨 A5 Visual + .pptx',   pct: 65 },
  { key: 'audit',        label: '🛡️ A9 Auditoría visual', pct: 75 },
  { key: 'reviewing',    label: '👥 A6/A7/A8 Revisores',  pct: 90 },
  { key: 'ready',        label: '✅ Listo',               pct: 100 },
];

function getStepIndex(status: string): number {
  const idx = PIPELINE_STEPS.findIndex((s) => s.key === status);
  return idx >= 0 ? idx : -1;
}

function ReviewInner() {
  const params = useSearchParams();
  const deckId = params.get('deckId') || '';
  const [deck, setDeck] = useState<any>(null);
  const [retrying, setRetrying] = useState(false);

  const refreshDeck = async () => {
    if (!deckId) return null;
    const d = await decks.get(deckId);
    setDeck(d);
    return d;
  };

  useEffect(() => {
    refreshDeck();
  }, [deckId]);

  // Polling activo
  useEffect(() => {
    if (!deck) return;
    const inProgress = ['generating','researching','structuring','writing','visual','audit','reviewing'].includes(deck.status);
    if (!inProgress) return;
    const id = setInterval(refreshDeck, 4000);
    return () => clearInterval(id);
  }, [deck?.status]);

  const handleCancel = async () => {
    if (!confirm('¿Cancelar la generación? Lo que esté en curso se detendrá tras el agente actual.')) return;
    try {
      await decks.cancel(deckId);
      await refreshDeck();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Error al cancelar');
    }
  };

  const handleGenerate = async () => {
    setRetrying(true);
    try {
      await generateApi.start(deckId);
      await refreshDeck();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Error al iniciar generación');
    } finally {
      setRetrying(false);
    }
  };

  if (!deck) return <AuthGuard><div className="text-stone-500">Cargando…</div></AuthGuard>;

  const inProgress = ['generating','researching','structuring','writing','visual','audit','reviewing'].includes(deck.status);
  const isError = deck.status === 'error';
  const isReady = deck.status === 'ready';
  const isCancelled = deck.status === 'cancelled';
  const isBlocked = deck.audit_status === 'BLOCKED';
  const isInitial = ['interviewing_done','draft'].includes(deck.status);
  const currentStepIdx = getStepIndex(deck.status);
  const pct = deck.progress_percentage || 0;

  return (
    <AuthGuard>
      <div className="max-w-4xl">
        <h1 className="text-3xl font-bold text-pruno mb-2">{deck.title}</h1>
        <p className="text-stone-600 mb-8">
          Cliente: <strong>{deck.client_name}</strong> · Tema: <strong>{deck.topic}</strong> · Estado:{' '}
          <strong className={isError ? 'text-magenta' : isReady ? 'text-verde' : 'text-amazonico'}>
            {deck.progress_step || deck.status}
          </strong>
        </p>

        {/* Botón de inicio si no ha arrancado */}
        {isInitial && (
          <div className="card mb-6">
            <h2 className="font-semibold text-pruno mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-magenta" /> Pipeline multi-agente
            </h2>
            <button onClick={handleGenerate} disabled={retrying} className="btn-magenta inline-flex items-center gap-2">
              <Sparkles className="w-4 h-4" /> {retrying ? 'Iniciando…' : 'Iniciar generación con IA'}
            </button>
          </div>
        )}

        {/* Barra de progreso */}
        {(inProgress || isReady || isError) && (
          <div className="card mb-6">
            <div className="flex justify-between items-center mb-3">
              <h2 className="font-semibold text-pruno flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-magenta" /> Progreso del pipeline
              </h2>
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold text-pruno">{pct}%</span>
                {inProgress && (
                  <button
                    onClick={handleCancel}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-chamfer border border-magenta text-magenta hover:bg-magenta/10 text-sm"
                  >
                    <StopCircle className="w-4 h-4" /> Cancelar
                  </button>
                )}
              </div>
            </div>
            <div className="h-3 bg-stone-200 rounded-full overflow-hidden mb-4">
              <div
                className={`h-3 rounded-full transition-all duration-500 ${
                  isError ? 'bg-magenta' : isReady ? 'bg-verde' : 'bg-magenta animate-pulse'
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>

            <div className="space-y-2">
              {PIPELINE_STEPS.map((step, i) => {
                let icon, color;
                if (isError && i === currentStepIdx) {
                  icon = <XCircle className="w-4 h-4 text-magenta" />;
                  color = 'text-magenta font-semibold';
                } else if (i < currentStepIdx || isReady) {
                  icon = <CheckCircle className="w-4 h-4 text-verde" />;
                  color = 'text-verde';
                } else if (i === currentStepIdx && inProgress) {
                  icon = <Loader2 className="w-4 h-4 text-amazonico animate-spin" />;
                  color = 'text-amazonico font-semibold';
                } else {
                  icon = <div className="w-4 h-4 rounded-full border-2 border-stone-300" />;
                  color = 'text-stone-400';
                }
                return (
                  <div key={step.key} className={`flex items-center gap-3 ${color}`}>
                    {icon}
                    <span className="text-sm">{step.label}</span>
                    {i === currentStepIdx && inProgress && (
                      <span className="text-xs text-stone-500 ml-auto">en curso…</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Cancelled */}
            {isCancelled && (
              <div className="mt-4 bg-stone-100 p-4 rounded-chamfer">
                <div className="flex items-center gap-2 text-stone-700 font-semibold mb-2">
                  <Ban className="w-4 h-4" /> Generación cancelada por el usuario
                </div>
                <p className="text-sm text-stone-600 mb-3">Puedes volver a iniciar el pipeline cuando quieras.</p>
                <button onClick={handleGenerate} disabled={retrying} className="btn-primary inline-flex items-center gap-2">
                  <RotateCw className="w-4 h-4" /> {retrying ? 'Reiniciando…' : 'Reiniciar generación'}
                </button>
              </div>
            )}

            {/* Error display */}
            {isError && deck.last_error && (
              <div className="mt-4 bg-magenta/10 p-4 rounded-chamfer">
                <div className="flex items-center gap-2 text-magenta font-semibold mb-2">
                  <AlertTriangle className="w-4 h-4" /> El pipeline se detuvo
                </div>
                <code className="block text-xs text-stone-700 font-mono mb-3 break-words">{deck.last_error}</code>
                <button onClick={handleGenerate} disabled={retrying} className="btn-primary inline-flex items-center gap-2">
                  <RotateCw className="w-4 h-4" /> {retrying ? 'Reintentando…' : 'Reintentar'}
                </button>
              </div>
            )}

            {/* Ready: descarga */}
            {isReady && (
              <div className="mt-4 flex items-center justify-between bg-verde/10 p-4 rounded-chamfer">
                <div className="flex items-center gap-2 text-verde">
                  <CheckCircle className="w-5 h-5" />
                  <span className="font-semibold">Deck listo · auditoría {deck.audit_status}</span>
                </div>
                <a href={decks.download(deck.id)} target="_blank" className="btn-primary inline-flex items-center gap-2">
                  <Download className="w-4 h-4" /> Descargar .pptx
                </a>
              </div>
            )}

            {/* Blocked */}
            {isBlocked && deck.status !== 'error' && (
              <div className="mt-4 bg-magenta/10 p-4 rounded-chamfer">
                <div className="flex items-center gap-2 text-magenta font-semibold mb-2">
                  <AlertTriangle className="w-4 h-4" /> Bloqueado por A9 (branding hostil detectado)
                </div>
                <p className="text-sm text-stone-700">Revisa el reporte abajo y reemplaza las imágenes flageadas antes de descargar.</p>
              </div>
            )}
          </div>
        )}

        {/* Audit report */}
        {deck.audit_report && Object.keys(deck.audit_report).length > 0 && (
          <div className="card mb-6">
            <h2 className="font-semibold text-pruno mb-4 flex items-center gap-2">
              {isBlocked ? <AlertTriangle className="w-5 h-5 text-magenta" /> : <CheckCircle className="w-5 h-5 text-verde" />}
              Auditoría visual A9 · <span className="font-mono text-sm">{deck.audit_status}</span>
            </h2>
            {deck.audit_report.summary && (
              <div className="grid grid-cols-4 gap-4 mb-4">
                <Stat label="Críticos" value={deck.audit_report.summary.critical} color="text-magenta" />
                <Stat label="Warnings" value={deck.audit_report.summary.warning} color="text-naranja" />
                <Stat label="Neutrales" value={deck.audit_report.summary.neutral} color="text-stone-600" />
                <Stat label="Aprobados" value={deck.audit_report.summary.approved} color="text-verde" />
              </div>
            )}
          </div>
        )}

        {/* Reviews */}
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
