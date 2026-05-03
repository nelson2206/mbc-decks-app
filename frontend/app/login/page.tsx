'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles } from 'lucide-react';
import { auth } from '@/lib/api';
import { useSession } from '@/lib/store';

export default function LoginPage() {
  const router = useRouter();
  const { setSession } = useSession();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await auth.login(email, password);
      setSession(data.access_token, {
        user_id: data.user_id,
        full_name: data.full_name,
        role: data.role,
      });
      router.push('/dashboard');
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Email o contraseña inválidos');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-pruno to-pruno-dark px-4">
      <div className="w-full max-w-md card">
        <div className="flex items-center gap-2 mb-6">
          <Sparkles className="w-7 h-7 text-magenta" />
          <h1 className="text-2xl font-bold text-pruno">MBC Decks</h1>
        </div>
        <p className="text-sm text-stone-600 mb-6">
          Generador de presentaciones Minsait Business Consulting
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Email corporativo</label>
            <input
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="input" placeholder="nombre@minsait.com"
            />
          </div>
          <div>
            <label className="label">Contraseña</label>
            <input
              type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="input"
            />
          </div>
          {error && <div className="text-sm text-magenta">{error}</div>}
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Ingresando…' : 'Ingresar'}
          </button>
        </form>
      </div>
    </div>
  );
}
