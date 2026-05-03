'use client';
import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { ArrowLeft, ArrowRight, BookOpen } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { AuthGuard } from '@/components/AuthGuard';
import { interview } from '@/lib/api';

type Q = { id: string; question: string; type: string; options?: string[]; required?: boolean };
type Block = { block: string; title: string; questions: Q[] };

function InterviewInner() {
  const params = useSearchParams();
  const router = useRouter();
  const deckId = params.get('deckId') || '';
  const [data, setData] = useState<any>(null);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!deckId) return;
    interview.questions(deckId).then(setData);
  }, [deckId]);

  if (!data) return <div className="text-stone-500">Cargando entrevista…</div>;

  const blocks: Block[] = data.base_blocks;
  const totalSteps = blocks.length + 1; // +1 para el bloque tema-específico
  const isTopicStep = step === blocks.length;
  const currentBlock = isTopicStep ? null : blocks[step];

  const handleNext = () => {
    if (step < totalSteps - 1) setStep(step + 1);
    else handleSubmit();
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await interview.submit(deckId, answers);
      router.push(`/new/review?deckId=${deckId}`);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Error guardando entrevista');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthGuard>
      <div className="max-w-3xl">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-pruno">Entrevista guiada</h1>
          <span className="text-sm text-stone-500">Paso {step + 1} de {totalSteps}</span>
        </div>
        <div className="h-1 bg-stone-200 rounded mb-8">
          <div className="h-1 bg-magenta rounded transition-all" style={{ width: `${((step + 1) / totalSteps) * 100}%` }} />
        </div>

        <div className="card mb-6">
          {currentBlock ? (
            <>
              <h2 className="text-xl font-semibold text-pruno mb-4">{currentBlock.title}</h2>
              <div className="space-y-5">
                {currentBlock.questions.map((q) => (
                  <div key={q.id}>
                    <label className="label">{q.question}</label>
                    {q.type === 'textarea' && (
                      <textarea
                        className="input min-h-24" value={answers[q.id] || ''}
                        onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                      />
                    )}
                    {(q.type === 'text' || q.type === 'date') && (
                      <input
                        type={q.type === 'date' ? 'date' : 'text'}
                        className="input" value={answers[q.id] || ''}
                        onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                      />
                    )}
                    {q.type === 'single_choice' && (
                      <select
                        className="input" value={answers[q.id] || ''}
                        onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                      >
                        <option value="">Selecciona…</option>
                        {q.options?.map((o) => <option key={o} value={o}>{o}</option>)}
                      </select>
                    )}
                    {q.type === 'file' && (
                      <input
                        type="file" className="input"
                        onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.files?.[0]?.name || '' })}
                      />
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-4">
                <BookOpen className="w-5 h-5 text-magenta" />
                <h2 className="text-xl font-semibold text-pruno">Bloque específico del tema · {data.topic}</h2>
              </div>
              <p className="text-sm text-stone-600 mb-4">
                Estas preguntas vienen del knowledge base. El A4 Contenido las usará para profundizar correctamente.
              </p>
              <div className="prose prose-sm max-w-none mb-4 p-4 bg-ceramica/30 rounded-chamfer">
                <ReactMarkdown>{data.topic_specific_markdown || '*(Sin knowledge base para este tema — el equipo MBC debe poblarlo)*'}</ReactMarkdown>
              </div>
              <textarea
                className="input min-h-32"
                placeholder="Escribe aquí las respuestas a las preguntas del bloque temático…"
                value={answers['P7_topic_specific'] || ''}
                onChange={(e) => setAnswers({ ...answers, P7_topic_specific: e.target.value })}
              />
            </>
          )}
        </div>

        <div className="flex justify-between">
          <button
            onClick={() => setStep(Math.max(0, step - 1))}
            disabled={step === 0}
            className="btn-secondary inline-flex items-center gap-2 disabled:opacity-50"
          >
            <ArrowLeft className="w-4 h-4" /> Atrás
          </button>
          <button onClick={handleNext} disabled={loading} className="btn-primary inline-flex items-center gap-2">
            {step === totalSteps - 1 ? (loading ? 'Guardando…' : 'Finalizar entrevista') : 'Siguiente'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </AuthGuard>
  );
}

export default function InterviewPage() {
  return <Suspense fallback={null}><InterviewInner /></Suspense>;
}
