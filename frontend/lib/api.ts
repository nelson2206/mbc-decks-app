// Cliente API para hablar con el backend FastAPI
import axios, { AxiosInstance } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Inyectar token JWT en cada request
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('mbc_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Logout automático en 401
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('mbc_token');
      if (window.location.pathname !== '/login') window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

// API calls
export const auth = {
  login: (email: string, password: string) =>
    api.post('/api/auth/login', { email, password }).then((r) => r.data),
  register: (email: string, password: string, full_name: string) =>
    api.post('/api/auth/register', { email, password, full_name }).then((r) => r.data),
};

export const decks = {
  list: () => api.get('/api/decks').then((r) => r.data),
  create: (req: any) => api.post('/api/decks', req).then((r) => r.data),
  get: (id: string) => api.get(`/api/decks/${id}`).then((r) => r.data),
  download: (id: string) => `${API_URL}/api/decks/${id}/download`,
  remove: (id: string) => api.delete(`/api/decks/${id}`),
};

export const interview = {
  topics: () => api.get('/api/interview/topics').then((r) => r.data),
  questions: (deckId: string) =>
    api.get(`/api/interview/${deckId}/questions`).then((r) => r.data),
  submit: (deckId: string, answers: Record<string, any>) =>
    api.post('/api/interview/submit', { deck_id: deckId, answers }).then((r) => r.data),
};

export const generateApi = {
  start: (deckId: string, opts?: any) =>
    api.post(`/api/generate/${deckId}`, { deck_id: deckId, ...opts }).then((r) => r.data),
};

export const auditApi = {
  run: (deckId: string) => api.post(`/api/audit/${deckId}`).then((r) => r.data),
  report: (deckId: string) => api.get(`/api/audit/${deckId}/report`).then((r) => r.data),
};

export const credentialsApi = {
  search: (params: { topic?: string; industry?: string; client?: string; keyword?: string }) =>
    api.get('/api/credentials', { params }).then((r) => r.data),
  topics: () => api.get('/api/credentials/topics').then((r) => r.data),
};
