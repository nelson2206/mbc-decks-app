'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/lib/store';

export default function Home() {
  const router = useRouter();
  const { token } = useSession();
  useEffect(() => {
    router.replace(token ? '/dashboard' : '/login');
  }, [token, router]);
  return null;
}
