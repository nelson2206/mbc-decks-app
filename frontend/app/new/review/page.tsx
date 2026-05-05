'use client';
import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Sparkles, AlertTriangle, CheckCircle, Loader2, Download, RotateCw, XCircle,
  StopCircle, Ban, Search, Layers, FileText, Image as ImageIcon, Shield,
  UserCheck, Briefcase, Cpu, Clock,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { AuthGuard } from '@/components/AuthGuard';
import { decks, generateApi, auditApi } from '@/lib/api';

type AgentStep = {
  key: string;
  label: string;
  short: string;
  desc: string;
  icon: any;
  pct: number;
  estSec: number;
};

const PIPELINE_STEPS: AgentStep[] = [
  { key: 'researching',  label: 'A2 · Investigador',       short: 'Research',  desc: 'Recopila data sectorial con fuentes citables',  icon: Search,     pct: 10, estSec: 70 },
  { key: 'structuring',  label: 'A3 · Estructurador MBB',  short: 'Structure', desc: 'Define la storyline consultiva (Pirámide Minto · MECE)', icon: Layers,    pct: 25, estSec: 60 },
  { key: 'writing',      label: 'A4 · Contenido + A6 Manager loop', short: 'Content', desc: 'Redacta cada slide y luego el Manager revisa. Si hay issues críticos, A4/A3 corrigen automático (max 2 iter)', icon: FileText, pct: 50, estSec: 150 },
  { key: 'visual',       label: 'A5 · Visual + .pptx',     short: 'Visual',    desc: 'Mapea slides a layouts oficiales y genera el .pptx', icon: ImageIcon, pct: 70, estSec: 10 },
  { key: 'audit',        label: 'A9 · Auditor visual',     short: 'Audit',     desc: 'Detecta branding hostil (competencia, otros clientes)', icon: Shield,    pct: 80, estSec: 20 },
  { key: 'reviewing',    label: 'A7/A8 · Socios',          short: 'Partners',  desc: 'Socio Consultoría + Socio Tech revisan el .pptx final (paralelo)', icon: UserCheck, pct: 92, estSec: 70 },
  { key: 'ready',        label: 'Listo',                   short: 'Done',      desc: 'Deck listo para descargar', icon: CheckCircle, pct: 100, estSec: 0 },
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
  const [fastMode, setFastMode] = useState(false);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [now, setNow] = useState<number>(Date.now());

  const refreshDeck = async () => {
    if (!deckId) return null;
    const d = await decks.get(deckId);
    setDeck(d);
    return d;
  };

  useEffect(() => { refreshDeck(); }, [deckId]);

  // Polling activo + reloj
  useEffect(() => {
    if (!deck) return;
    const inProgress = ['generating','researching','structuring','writing','visual','audit','reviewing'].includes(deck.status);
    if (!inProgress) return;
    if (!startTime) setStartTime(Date.now());
    const id = setInterval(() => {
      refreshDeck();
      setNow(Date.now());
    }, 4000);
    return () => clearInterval(id);
  }, [deck?.status]);

  const handleGenerate = async () => {
    setRetrying(true);
    setStartTime(Date.now());
    try {
      await generateApi.start(deckId, { fast_mode: fastMode });
      await refreshDeck();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Error al iniciar');
    } finally {
      setRetrying(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm('¿Detener la generación? El agente actual completará pero los siguientes se omitirán.')) return;
    try {
      await decks.cancel(deckId);
      await refreshDeck();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Error al detener');
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
  const elapsed = startTime ? Math.floor((now - startTime)/1000) : 0;
  const totalEstimate = fastMode ? 230 : 380;  // turbo: A2+A3+A4+pptx ~230s · full: ~380s con manager loop + partners + A9
  const remaining = Math.max(totalEstimate - elapsed, 0);

  return (
    <AuthGuard>
      <div className="max-w-5xl">
        {/* Header con título y meta */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-pruno mb-1">{deck.title}</h1>
          <div className="flex items-center gap-3 text-sm text-stone-600">
            <span>Cliente: <strong className="text-pruno">{deck.client_name}</strong></span>
            <span>·</span>
            <span>Tema: <strong className="text-pruno">{deck.topic}</strong></span>
            <span>·</span>
            <span>Industria: <strong className="text-pruno">{deck.industry?.replace(/_/g,' ')}</strong></span>
          </div>
        </div>

        {/* Botón inicial */}
        {isInitial && (
          <div className="card mb-6 border-l-4 border-magenta">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-6 h-6 text-magenta" />
              <h2 className="text-xl font-bold text-pruno">Pipeline multi-agente listo para arrancar</h2>
            </div>
            <p className="text-sm text-stone-600 mb-4">
              7 agentes especializados trabajarán en cadena para producir tu deck. Tiempo total: <strong>~5 min</strong> (completo) o <strong>~3 min</strong> (rápido).
            </p>

            {/* Preview de los 7 agentes */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-5">
              {PIPELINE_STEPS.slice(0, 6).map((s) => {
                const Icon = s.icon;
                const skipped = fastMode && (s.key === 'reviewing' || s.key === 'audit');
                return (
                  <div key={s.key} className={`flex items-start gap-2 p-2 rounded-chamfer ${skipped ? 'opacity-40 line-through' : 'bg-ceramica/30'}`}>
                    <Icon className="w-4 h-4 text-pruno mt-0.5 flex-shrink-0" />
                    <div>
                      <div className="text-xs font-semibold text-pruno">{s.label}</div>
                      <div className="text-xs text-stone-600">{s.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>

            <label className="flex items-start gap-3 mb-4 cursor-pointer p-3 rounded-chamfer border border-stone-200 hover:bg-stone-50">
              <input type="checkbox" checked={fastMode} onChange={(e) => setFastMode(e.target.checked)} className="w-4 h-4 accent-magenta mt-0.5" />
              <div>
                <span className="text-sm font-semibold text-pruno">⚡ Modo Turbo</span>
                <span className="block text-xs text-stone-600 mt-1 leading-relaxed">
                  Salta TODAS las revisiones — A6 Manager loop, A7 Partner Consulting, A8 Partner Tech y A9 Auditor visual.
                  Solo corren A2, A3, A4 y la generación del .pptx. Termina en ~2 min en lugar de ~4-5 min.
                </span>
                <span className="block text-xs text-naranja mt-1">
                  ⚠️ Sin verificación de branding hostil ni feedback estratégico. Solo para drafts rápidos.
                </span>
              </div>
            </label>

            <button onClick={handleGenerate} disabled={retrying} className="btn-magenta inline-flex items-center gap-2">
              <Sparkles className="w-4 h-4" /> {retrying ? 'Iniciando…' : `Iniciar generación${fastMode ? ' (Turbo)' : ''}`}
            </button>
          </div>
        )}

        {/* Barra de progreso general (cuando hay actividad) */}
        {(inProgress || isReady || isError || isCancelled) && (
          <div className="card mb-6">
            <div className="flex items-start justify-between mb-4 flex-wrap gap-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles className="w-5 h-5 text-magenta" />
                  <h2 className="font-bold text-pruno text-lg">Pipeline multi-agente</h2>
                </div>
                <p className="text-sm text-stone-600">
                  {isReady ? '✅ Completado' : isError ? '⚠ Error' : isCancelled ? '⏸ Cancelado' : `Ejecutando · ${deck.progress_step || 'iniciando'}`}
                </p>
              </div>
              <div className="flex items-center gap-3">
                {inProgress && (
                  <div className="flex items-center gap-1 text-sm text-stone-500">
                    <Clock className="w-4 h-4" />
                    <span>{Math.floor(elapsed/60)}:{String(elapsed%60).padStart(2,'0')}</span>
                    <span className="text-xs">/ ~{Math.floor(totalEstimate/60)} min</span>
                  </div>
                )}
                <div className={`text-3xl font-bold ${isError ? 'text-magenta' : isReady ? 'text-verde' : 'text-pruno'}`}>{pct}%</div>
                {(inProgress || isError) && (
                  <button onClick={handleCancel} className="inline-flex items-center gap-1 px-3 py-2 rounded-chamfer border border-magenta text-magenta hover:bg-magenta hover:text-white text-sm font-medium transition">
                    <StopCircle className="w-4 h-4" /> Detener
                  </button>
                )}
              </div>
            </div>

            {/* Barra principal */}
            <div className="h-3 bg-stone-200 rounded-full overflow-hidden mb-6 relative">
              <div
                className={`h-3 rounded-full transition-all duration-700 ${
                  isError ? 'bg-magenta' : isReady ? 'bg-verde' : isCancelled ? 'bg-stone-400' : 'bg-gradient-to-r from-magenta to-lila animate-pulse'
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>

            {/* Cards por agente */}
            <div className="space-y-2">
              {PIPELINE_STEPS.slice(0, 7).map((step, i) => {
                const Icon = step.icon;
                let cardClass = '', iconBg = '', textColor = '', timeLabel = '';
                if (isError && i === currentStepIdx) {
                  cardClass = 'bg-magenta/5 border-magenta';
                  iconBg = 'bg-magenta text-white';
                  textColor = 'text-magenta';
                  timeLabel = 'Falló';
                } else if (i < currentStepIdx || isReady) {
                  cardClass = 'bg-verde/5 border-verde/30';
                  iconBg = 'bg-verde text-white';
                  textColor = 'text-verde';
                  timeLabel = `~${step.estSec}s`;
                } else if (i === currentStepIdx && inProgress) {
                  cardClass = 'bg-amazonico/5 border-amazonico animate-pulse';
                  iconBg = 'bg-amazonico text-white';
                  textColor = 'text-amazonico';
                  timeLabel = 'En curso…';
                } else {
                  cardClass = 'bg-stone-50 border-stone-200';
                  iconBg = 'bg-stone-200 text-stone-400';
                  textColor = 'text-stone-400';
                  timeLabel = `~${step.estSec}s`;
                }
                const isCurrent = i === currentStepIdx && inProgress;
                return (
                  <div key={step.key} className={`flex items-center gap-3 p-3 rounded-chamfer border ${cardClass}`}>
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center ${iconBg} flex-shrink-0`}>
                      {isCurrent ? <Loader2 className="w-5 h-5 animate-spin" /> :
                       isError && i === currentStepIdx ? <XCircle className="w-5 h-5" /> :
                       (i < currentStepIdx || isReady) ? <CheckCircle className="w-5 h-5" /> :
                       <Icon className="w-5 h-5" />}
                    </div>
                    <div className="flex-1">
                      <div className={`text-sm font-semibold ${textColor}`}>{step.label}</div>
                      <div className="text-xs text-stone-600">{step.desc}</div>
                    </div>
                    <div className={`text-xs ${textColor} text-right whitespace-nowrap`}>{timeLabel}</div>
                  </div>
                );
              })}
            </div>

            {/* Cancelado */}
            {isCancelled && (
              <div className="mt-5 bg-stone-100 p-4 rounded-chamfer border border-stone-300">
                <div className="flex items-center gap-2 text-stone-700 font-semibold mb-2"><Ban className="w-4 h-4" /> Generación detenida</div>
                <p className="text-sm text-stone-600 mb-3">{deck.last_error || 'Cancelado por el usuario'}</p>
                <button onClick={handleGenerate} disabled={retrying} className="btn-primary inline-flex items-center gap-2">
                  <RotateCw className="w-4 h-4" /> {retrying ? 'Reiniciando…' : 'Reiniciar'}
                </button>
              </div>
            )}

            {/* Error */}
            {isError && (
              <div className="mt-5 bg-magenta/10 p-4 rounded-chamfer border border-magenta/30">
                <div className="flex items-center gap-2 text-magenta font-semibold mb-2"><AlertTriangle className="w-4 h-4" /> El pipeline se detuvo</div>
                <code className="block text-xs text-stone-700 font-mono mb-3 break-words bg-white p-2 rounded">{deck.last_error || 'Error desconocido'}</code>
                <div className="flex gap-2">
                  <button onClick={handleGenerate} disabled={retrying} className="btn-primary inline-flex items-center gap-2">
                    <RotateCw className="w-4 h-4" /> {retrying ? 'Reintentando…' : 'Reintentar'}
                  </button>
                  <button onClick={handleCancel} className="btn-secondary inline-flex items-center gap-2">
                    <Ban className="w-4 h-4" /> Marcar como cancelado
                  </button>
                </div>
              </div>
            )}

            {/* Ready: descarga + regenerar */}
            {isReady && (
              <div className="mt-5 flex items-center justify-between bg-gradient-to-r from-verde/10 to-amazonico/10 p-4 rounded-chamfer border border-verde/30">
                <div className="flex items-center gap-2 text-verde">
                  <CheckCircle className="w-6 h-6" />
                  <div>
                    <div className="font-bold">Deck listo</div>
                    <div className="text-xs text-stone-600">Auditoría visual: <strong>{deck.audit_status}</strong></div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={async () => {
                      if (!confirm('¿Regenerar el deck con el mismo prompt? Toma 3-5 min y reemplaza el .pptx actual.')) return;
                      await handleGenerate();
                    }}
                    disabled={retrying}
                    className="btn-secondary inline-flex items-center gap-2"
                    title="Re-corre todo el pipeline usando el mismo brief y entrevista"
                  >
                    <RotateCw className="w-4 h-4" /> Regenerar
                  </button>
                  <button
                    onClick={async (e) => {
                      e.preventDefault();
                      try { await decks.download(deck.id, `${deck.client_name}_${deck.title}.pptx`); }
                      catch (err: any) { alert(err.message || 'Error al descargar'); }
                    }}
                    className="btn-primary inline-flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" /> Descargar .pptx
                  </button>
                </div>
              </div>
            )}

            {/* Blocked */}
            {isBlocked && deck.status !== 'error' && (
              <div className="mt-5 bg-magenta/10 p-4 rounded-chamfer border border-magenta/30">
                <div className="flex items-center gap-2 text-magenta font-semibold mb-2"><AlertTriangle className="w-4 h-4" /> Bloqueado por A9 (branding hostil)</div>
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
              <div className="grid grid-cols-4 gap-4">
                <Stat label="🚨 Críticos"  value={deck.audit_report.summary.critical} color="text-magenta" />
                <Stat label="⚠ Warnings"  value={deck.audit_report.summary.warning}  color="text-naranja" />
                <Stat label="ℹ Neutrales" value={deck.audit_report.summary.neutral}  color="text-stone-600" />
                <Stat label="✅ Aprobados" value={deck.audit_report.summary.approved} color="text-verde" />
              </div>
            )}
          </div>
        )}

        {/* Reviews */}
        {deck.review_consolidated && (
          <div className="card">
            <h2 className="font-semibold text-pruno mb-4 flex items-center gap-2"><Briefcase className="w-5 h-5 text-magenta" /> Revisión Manager + Socios</h2>
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
      <div className={`text-3xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-stone-600 mt-1">{label}</div>
    </div>
  );
}

export default function ReviewPage() {
  return <Suspense fallback={null}><ReviewInner /></Suspense>;
}
