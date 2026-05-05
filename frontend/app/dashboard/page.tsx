'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Download, AlertCircle, CheckCircle, Clock, Loader2, RotateCw } from 'lucide-react';
import { AuthGuard } from '@/components/AuthGuard';
import { decks, generateApi } from '@/lib/api';

type DeckItem = {
  id: string;
  title: string;
  client_name: string;
  topic: string;
  status: string;
  audit_status: string;
  updated_at: string;
};

const STATUS_LABEL: Record<string, { label: string; icon: any; color: string }> = {
  draft: { label: 'Borrador', icon: Clock, color: 'text-stone-500' },
  interviewing: { label: 'En entrevista', icon: Clock, color: 'text-amazonico' },
  interviewing_done: { label: 'Listo para generar', icon: CheckCircle, color: 'text-verde' },
  researching: { label: 'Investigando', icon: Loader2, color: 'text-amazonico' },
  structuring: { label: 'Estructurando', icon: Loader2, color: 'text-lila' },
  writing: { label: 'Redactando', icon: Loader2, color: 'text-lila' },
  visual: { label: 'Visual', icon: Loader2, color: 'text-naranja' },
  audit: { label: 'En auditoría', icon: Loader2, color: 'text-naranja' },
  blocked: { label: 'Bloqueado', icon: AlertCircle, color: 'text-magenta' },
  ready: { label: 'Listo', icon: CheckCircle, color: 'text-verde' },
  delivered: { label: 'Entregado', icon: CheckCircle, color: 'text-verde' },
};

export default function DashboardPage() {
  const [items, setItems] = useState<DeckItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [regenModal, setRegenModal] = useState<{deck: DeckItem | null; turbo: boolean}>({
    deck: null, turbo: false,
  });

  useEffect(() => {
    decks.list().then(setItems).finally(() => setLoading(false));
  }, []);

  const handleRegenerate = async () => {
    if (!regenModal.deck) return;
    const d = regenModal.deck;
    const turbo = regenModal.turbo;
    setRegenModal({ deck: null, turbo: false });
    try {
      await generateApi.start(d.id, { fast_mode: turbo });
      decks.list().then(setItems);
      alert(`Regeneración iniciada${turbo ? " (modo turbo)" : ""}. Mira el progreso en "Ver / Editar".`);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Error al regenerar");
    }
  };

  return (
    <AuthGuard>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-pruno">Mis decks</h1>
          {/* build: 2026-05-04T23:38 — botón Regenerar desplegado */}
          <p className="text-stone-600 mt-1">Tus presentaciones generadas con MBC Decks</p>
        </div>
        <Link href="/new" className="btn-primary inline-flex items-center gap-2">
          <Plus className="w-4 h-4" /> Nuevo deck
        </Link>
      </div>

      {loading ? (
        <p className="text-stone-500">Cargando…</p>
      ) : items.length === 0 ? (
        <div className="card text-center py-16">
          <h3 className="text-xl font-semibold text-pruno mb-2">Aún no tienes decks</h3>
          <p className="text-stone-600 mb-6">Empieza creando tu primera propuesta o presentación</p>
          <Link href="/new" className="btn-primary inline-flex items-center gap-2">
            <Plus className="w-4 h-4" /> Crear primer deck
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {items.map((d) => {
            const status = STATUS_LABEL[d.status] ?? STATUS_LABEL.draft;
            const Icon = status.icon;
            const blocked = d.audit_status === 'BLOCKED';
            return (
              <div key={d.id} className="card flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-pruno">{d.title}</h3>
                    <span className="text-xs px-2 py-0.5 bg-ceramica rounded-full text-pruno">{d.topic}</span>
                  </div>
                  <p className="text-sm text-stone-600 mt-1">Cliente: {d.client_name}</p>
                  <div className={`flex items-center gap-1 mt-2 text-xs ${status.color}`}>
                    <Icon className="w-3 h-3" />
                    <span>{status.label}</span>
                    {blocked && <span className="ml-2 text-magenta">⚠ Branding hostil detectado</span>}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Link href={`/new/review?deckId=${d.id}`} className="btn-secondary text-sm">
                    Ver / Editar
                  </Link>
                  {(d.status === 'ready' || d.status === 'error' || d.status === 'blocked') && (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        setRegenModal({ deck: d, turbo: false });
                      }}
                      className="btn-secondary text-sm inline-flex items-center gap-1"
                      title="Re-corre el pipeline con el mismo brief"
                    >
                      <RotateCw className="w-3 h-3" /> Regenerar
                    </button>
                  )}
                  {d.status === 'ready' && (
                    <button
                      onClick={async (e) => {
                        e.preventDefault();
                        try { await decks.download(d.id, `${d.client_name}_${d.title}.pptx`); }
                        catch (err: any) { alert(err.message || 'Error al descargar'); }
                      }}
                      className="btn-primary text-sm inline-flex items-center gap-1"
                    >
                      <Download className="w-3 h-3" /> Descargar
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Regenerar con toggle de modo turbo */}
      {regenModal.deck && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={() => setRegenModal({ deck: null, turbo: false })}
        >
          <div
            className="bg-white rounded-chamfer p-6 max-w-md w-full mx-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xl font-bold text-pruno mb-2">Regenerar deck</h3>
            <p className="text-sm text-stone-600 mb-4">
              Vas a re-correr el pipeline completo para <strong>"{regenModal.deck.title}"</strong> usando el mismo brief y entrevista. Esto reemplazará el .pptx actual.
            </p>

            <label className="flex items-start gap-3 p-3 border border-stone-200 rounded-chamfer cursor-pointer hover:border-pruno mb-4">
              <input
                type="checkbox"
                checked={regenModal.turbo}
                onChange={(e) => setRegenModal({ ...regenModal, turbo: e.target.checked })}
                className="w-4 h-4 accent-magenta mt-0.5"
              />
              <div>
                <div className="font-semibold text-pruno text-sm">⚡ Modo Turbo</div>
                <div className="text-xs text-stone-600 mt-0.5 leading-relaxed">
                  Salta TODAS las revisiones — A6 Manager, A7 Partner Consulting, A8 Partner Tech y A9 Auditor Visual. Solo corren A2 Investigador, A3 Estructurador, A4 Contenido y la generación del .pptx.
                  <br />
                  ⚠️ El deck saldrá sin verificar branding hostil ni feedback de los Socios. Útil para draft rápido.
                </div>
              </div>
            </label>

            <div className="text-xs text-stone-500 mb-4">
              Tiempo estimado: <strong>{regenModal.turbo ? "~2 min" : "~4-5 min"}</strong>
              {regenModal.turbo && <span className="ml-2 text-naranja">· sin Manager · sin Partners · sin A9</span>}
            </div>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setRegenModal({ deck: null, turbo: false })}
                className="btn-secondary text-sm"
              >
                Cancelar
              </button>
              <button
                onClick={handleRegenerate}
                className="btn-primary text-sm inline-flex items-center gap-2"
              >
                <RotateCw className="w-4 h-4" />
                {regenModal.turbo ? "Regenerar Turbo" : "Regenerar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthGuard>
  );
}
