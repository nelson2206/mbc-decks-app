'use client';
import { useEffect, useState } from 'react';
import { Search, Filter, FileText } from 'lucide-react';
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

export default function CredentialsPage() {
  const [items, setItems] = useState<Credential[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [filters, setFilters] = useState({ topic: '', industry: '', keyword: '' });
  const [loading, setLoading] = useState(true);

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

  return (
    <AuthGuard>
      <div className="max-w-5xl">
        <h1 className="text-3xl font-bold text-pruno mb-2">Biblioteca de credenciales</h1>
        <p className="text-stone-600 mb-6">Casos de éxito reusables para enriquecer tus propuestas</p>

        <div className="card mb-6 grid md:grid-cols-4 gap-3">
          <select className="input" value={filters.topic} onChange={(e) => setFilters({ ...filters, topic: e.target.value })}>
            <option value="">Todos los temas</option>
            {topics.map((t) => <option key={t} value={t}>{t}</option>)}
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
              <div key={c.id} className="card hover:border-magenta transition cursor-pointer">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs px-2 py-0.5 bg-pruno text-white rounded-full">{c.topic}</span>
                  {c.year && <span className="text-xs text-stone-500">{c.year}</span>}
                </div>
                <h3 className="font-semibold text-pruno">{c.client}</h3>
                <p className="text-xs text-stone-600 mt-1">{c.industry}</p>
                <p className="text-xs text-stone-500 mt-2 line-clamp-3">
                  {c.metadata_json?.slide_text_preview || 'Sin descripción'}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
