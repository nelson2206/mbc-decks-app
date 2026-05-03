'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Download, AlertCircle, CheckCircle, Clock, Loader2 } from 'lucide-react';
import { AuthGuard } from '@/components/AuthGuard';
import { decks } from '@/lib/api';

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

  useEffect(() => {
    decks.list().then(setItems).finally(() => setLoading(false));
  }, []);

  return (
    <AuthGuard>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-pruno">Mis decks</h1>
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
                  {d.status === 'ready' && (
                    <a
                      href={decks.download(d.id)} target="_blank"
                      className="btn-primary text-sm inline-flex items-center gap-1"
                    >
                      <Download className="w-3 h-3" /> Descargar
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </AuthGuard>
  );
}
