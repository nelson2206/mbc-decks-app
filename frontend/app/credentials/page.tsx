'use client';
import { useEffect, useState } from 'react';
import { Search, FileText, X, Calendar, Building, Tag, Briefcase, ExternalLink } from 'lucide-react';
import { AuthGuard } from '@/components/AuthGuard';
import { credentialsApi } from '@/lib/api';

type Credential = {
  id: string;
  client: string;
  industry: string;
  topic: string;
  year: number | null;
  metadata_json: any;
};

type Detail = {
  id: string;
  client: string;
  industry: string;
  topic: string;
  year: number | null;
  title: string;
  source_deck: string;
  bullets: string[];
  raw_text: string;
};

const TOPIC_LABELS: Record<string, string> = {
  pmo: 'PMO · Project Management',
  data_analytics: 'Data & Analytics',
  ia_genai: 'Generative AI / Agentes',
  transformacion_digital: 'Transformación Digital',
  modelo_operativo: 'Modelo Operativo',
  capabilities: 'Capabilities',
  ciberseguridad: 'Ciberseguridad',
  esg: 'ESG',
  eficiencia_operacional: 'Eficiencia Operacional',
};

const INDUSTRY_LABELS: Record<string, string> = {
  industria_consumo_energia: 'Industria, Consumo y Energía',
  servicios_financieros: 'Servicios Financieros',
};

export default function CredentialsPage() {
  const [items, setItems] = useState<Credential[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [filters, setFilters] = useState({ topic: '', industry: '', keyword: '' });
  const [loading, setLoading] = useState(true);
  const [previewing, setPreviewing] = useState<Detail | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    credentialsApi.topics().then((d) => setTopics(d.topics || []));
    fetchItems();
  }, []);

  const fetchItems = async () => {
    setLoading(true);
    try {
      const data = await credentialsApi.search({
        topic: filters.topic || undefined,
        industry: filters.industry || undefined,
        keyword: filters.keyword || undefined,
      });
      setItems(data);
    } finally {
      setLoading(false);
    }
  };

  const openPreview = async (id: string) => {
    setPreviewLoading(true);
    setPreviewing(null);
    try {
      const detail = await credentialsApi.detail(id);
      setPreviewing(detail);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'No se pudo cargar el preview');
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <AuthGuard>
      <div className="max-w-6xl">
        <h1 className="text-3xl font-bold text-pruno mb-2">Biblioteca de credenciales</h1>
        <p className="text-stone-600 mb-6">Casos de éxito reusables para enriquecer tus propuestas. Click en cualquier card para ver el preview del slide.</p>

        <div className="card mb-6 grid md:grid-cols-4 gap-3">
          <select className="input" value={filters.topic} onChange={(e) => setFilters({ ...filters, topic: e.target.value })}>
            <option value="">Todos los temas</option>
            {topics.map((t) => <option key={t} value={t}>{TOPIC_LABELS[t] || t}</option>)}
          </select>
          <select className="input" value={filters.industry} onChange={(e) => setFilters({ ...filters, industry: e.target.value })}>
            <option value="">Todas las industrias</option>
            <option value="industria_consumo_energia">Industria, Consumo y Energía</option>
            <option value="servicios_financieros">Servicios Financieros</option>
          </select>
          <input
            className="input md:col-span-2"
            placeholder="Buscar por cliente o keyword..."
            value={filters.keyword}
            onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
            onKeyDown={(e) => e.key === 'Enter' && fetchItems()}
          />
        </div>

        <button onClick={fetchItems} className="btn-primary inline-flex items-center gap-2 mb-6">
          <Search className="w-4 h-4" /> Buscar
        </button>

        {loading ? (
          <p className="text-stone-500">Cargando…</p>
        ) : items.length === 0 ? (
          <div className="card text-center py-12">
            <FileText className="w-10 h-10 text-stone-400 mx-auto mb-3" />
            <p className="text-stone-600">No hay credenciales que coincidan con los filtros</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((c) => (
              <button
                key={c.id}
                onClick={() => openPreview(c.id)}
                className="card hover:border-magenta hover:shadow-lg transition cursor-pointer text-left flex flex-col"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs px-2 py-0.5 bg-pruno text-white rounded-full">{TOPIC_LABELS[c.topic] || c.topic}</span>
                  {c.year && <span className="text-xs text-stone-500">{c.year}</span>}
                </div>
                <h3 className="font-bold text-pruno text-lg">{c.client}</h3>
                <p className="text-xs text-stone-600 mt-1 mb-2 flex items-center gap-1">
                  <Building className="w-3 h-3" /> {INDUSTRY_LABELS[c.industry] || c.industry}
                </p>
                <p className="text-xs text-stone-500 line-clamp-3 flex-1">
                  {c.metadata_json?.title || c.metadata_json?.slide_text_preview || 'Click para ver detalles'}
                </p>
                <span className="text-xs text-magenta mt-2 font-semibold inline-flex items-center gap-1">
                  Ver preview <ExternalLink className="w-3 h-3" />
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Modal de preview tipo slide Minsait */}
        {previewing && (
          <div
            className="fixed inset-0 bg-pruno-dark/80 backdrop-blur-sm z-50 flex items-center justify-center p-6"
            onClick={() => setPreviewing(null)}
          >
            <div
              className="bg-white rounded-chamfer shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Slide preview · estilo Minsait con fondo Pruno */}
              <div className="bg-gradient-to-br from-pruno to-pruno-dark text-white p-10 relative">
                <button
                  onClick={() => setPreviewing(null)}
                  className="absolute top-4 right-4 w-9 h-9 bg-white/10 hover:bg-magenta rounded-full flex items-center justify-center transition"
                >
                  <X className="w-5 h-5" />
                </button>
                <div className="flex items-center gap-2 text-xs text-ceramica/70 mb-3">
                  <span className="px-2 py-0.5 bg-magenta rounded-full text-white font-semibold">
                    {TOPIC_LABELS[previewing.topic] || previewing.topic}
                  </span>
                  <Building className="w-3 h-3" />
                  <span>{INDUSTRY_LABELS[previewing.industry] || previewing.industry}</span>
                  {previewing.year && <><Calendar className="w-3 h-3" /><span>{previewing.year}</span></>}
                </div>
                <h2 className="text-4xl font-bold mb-4">{previewing.client}</h2>
                {previewing.title && (
                  <p className="text-lg text-ceramica/90 mb-4 leading-relaxed">{previewing.title}</p>
                )}
                <div className="text-xs text-ceramica/60 mt-6 pt-4 border-t border-white/20">
                  MINSAIT · Caso de éxito · {previewing.client}
                </div>
              </div>

              {/* Detalle scrollable */}
              <div className="overflow-y-auto p-6 bg-stone-50">
                <h3 className="text-sm font-bold text-pruno mb-3 flex items-center gap-2">
                  <Briefcase className="w-4 h-4" /> Contenido del slide
                </h3>
                <div className="space-y-2 mb-6">
                  {previewing.bullets.map((b, i) => (
                    <div key={i} className="flex gap-2 text-sm text-stone-700">
                      <span className="text-magenta font-bold flex-shrink-0">·</span>
                      <span>{b}</span>
                    </div>
                  ))}
                </div>

                <div className="border-t border-stone-200 pt-4 grid grid-cols-2 gap-4 text-xs text-stone-600">
                  <div>
                    <div className="font-semibold text-pruno mb-1 flex items-center gap-1">
                      <Tag className="w-3 h-3" /> Identificador
                    </div>
                    <code className="text-xs bg-white p-1 rounded">{previewing.id}</code>
                  </div>
                  {previewing.source_deck && (
                    <div>
                      <div className="font-semibold text-pruno mb-1">Deck origen</div>
                      <div className="text-xs">{previewing.source_deck}</div>
                    </div>
                  )}
                </div>

                <div className="mt-4 p-3 bg-amazonico/10 rounded-chamfer text-xs text-stone-700">
                  💡 <strong>Esta credencial puede ser incluida</strong> automáticamente en una propuesta nueva del mismo tema/industria, o citada en el slide "Casos de éxito" del deck en generación.
                </div>
              </div>
            </div>
          </div>
        )}

        {previewLoading && (
          <div className="fixed inset-0 bg-pruno-dark/80 z-50 flex items-center justify-center">
            <div className="text-white">Cargando preview…</div>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
