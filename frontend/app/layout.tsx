import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'MBC Decks · Generador de presentaciones Minsait',
  description: 'Generador de propuestas comerciales y técnicas con marca Minsait Business Consulting',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
