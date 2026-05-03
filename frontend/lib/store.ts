// Zustand store para gestionar estado de auth + sesión actual
import { create } from 'zustand';

type User = {
  user_id: string;
  full_name: string;
  role: string;
};

type State = {
  user: User | null;
  token: string | null;
  setSession: (token: string, user: User) => void;
  clearSession: () => void;
};

export const useSession = create<State>((set) => ({
  user: typeof window !== 'undefined' ? JSON.parse(localStorage.getItem('mbc_user') || 'null') : null,
  token: typeof window !== 'undefined' ? localStorage.getItem('mbc_token') : null,
  setSession: (token, user) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('mbc_token', token);
      localStorage.setItem('mbc_user', JSON.stringify(user));
    }
    set({ token, user });
  },
  clearSession: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('mbc_token');
      localStorage.removeItem('mbc_user');
    }
    set({ token: null, user: null });
  },
}));
