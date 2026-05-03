'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight } from 'lucide-react';
import { AuthGuard } from '@/components/AuthGuard';
import { decks, interview } from '@/lib/api';

const DECK_TYPES = [
  { id: 'proposal_commercial', label: 'Propuesta comercial', desc: 'Venta consultiva con co-branding cliente' },
  { id: 'proposal_technical', label: 'Oferta técnica (OT/OE)', desc: 'Propuesta densa con stack y arquitectura' },
  { id: 'proposal_capabilities', label: 'Capabilities', desc: 'Capacidades MBC en una práctica/sector' },
  { id: 'proposal_assessment', label: 'Assessment de madurez', desc: 'Diagnóstico con framework + roadmap' },
  { id: 'proposal_initiation', label: 'Iniciación de proyecto', desc: 'Kickoff post-venta' },
  { id: 'training_internal', label: 'Capacitación interna', desc: '100% Minsait, sin co-branding' },
];

const INDUSTRIES = [
  { id: 'industria_consumo_energia', label: 'Industria, Consumo y Energía' },
  { id: 'servicios_financieros', label: 'Servicios Financieros' },
  { id: 'sector_publico', label: 'Sector Público' },
  { id: 'salud', label: 'Salud' },
  { id: 'educacion', label: 'Educación' },
  { id: 'all', label: 'Cualquiera (interno)' },
];

export default function NewDeckPage() {
  const router = useRouter();
  const [topics, setTopics] = useState<string[]>([]);
  const [form, setForm] = useState({
    deck_type: '',
    topic: '',
    industry: '',
    title_working: '',
    client_name: '',
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    interview.topics().then((d) => setTopics(d.topics || []));
  }, []);

  const canSubmit = form.deck_type && form.topic && form.industry && form.title_working && form.client_name;

  const handleStart = async () => {
    setLoading(true);
    try {
      const deck = await decks.create(form);
      router.push(`/new/interview?deckId=${deck.id}`);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Error creando el deck');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthGuard>
      <div className="max-w-3xl">
        <h1 className="text-3xl font-bold text-pruno mb-2">Nuevo deck</h1>
        <p className="text-stone-600 mb-8">Empieza definiendo el tipo, tema y cliente — luego pasamos a la entrevista guiada.</p>

        <section className="space-y-6">
          <div>
            <label className="label">Tipo de deck</label>
            <div className="grid md:grid-cols-2 gap-3">
              {DECK_TYPES.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setForm({ ...form, deck_type: t.id })}
                  className={`text-left p-4 rounded-chamfer border transition ${
                    form.deck_type === t.id ? 'border-magenta bg-magenta/5' : 'border-stone-200 hover:border-pruno'
                  }`}
                >
                  <div className="font-semibold text-pruno text-sm">{t.label}</div>
                  <div className="text-xs text-stone-600 mt-1">{t.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="label">Tema (knowledge base)</label>
              <select className="input" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })}>
                <option value="">Selecciona…</option>
                {topics.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <p className="text-xs text-stone-500 mt-1">El A4 Contenido cargará el knowledge de este tema</p>
            </div>
            <div>
              <label className="label">Industria del cliente</label>
              <select className="input" value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })}>
                <option value="">Selecciona…</option>
                {INDUSTRIES.map((i) => <option key={i.id} value={i.id}>{i.label}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="label">Título de trabajo del deck</label>
            <input
              className="input" value={form.title_working}
              onChange={(e) => setForm({ ...form, title_working: e.target.value })}
              placeholder="Ej: PMO Avanzada · Project Acceleration Hub 2.0"
            />
          </div>

          <div>
            <label className="label">Cliente</label>
            <input
              className="input" value={form.client_name}
              onChange={(e) => setForm({ ...form, client_name: e.target.value })}
              placeholder="Ej: Ferreyros"
            />
          </div>

          <button
            onClick={handleStart}
            disabled={!canSubmit || loading}
            className="btn-primary inline-flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? 'Creando…' : 'Continuar a entrevista'} <ArrowRight className="w-4 h-4" />
          </button>
        </section>
      </div>
    </AuthGuard>
  );
}
