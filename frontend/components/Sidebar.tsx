'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LayoutDashboard, Plus, BookOpen, LogOut, Sparkles } from 'lucide-react';
import { useSession } from '@/lib/store';

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearSession } = useSession();

  const navItems = [
    { href: '/dashboard', label: 'Mis decks', icon: LayoutDashboard },
    { href: '/new', label: 'Nuevo deck', icon: Plus },
    { href: '/credentials', label: 'Credenciales', icon: BookOpen },
  ];

  const isActive = (href: string) => pathname === href || pathname?.startsWith(`${href}/`);

  return (
    <aside className="w-64 bg-pruno text-white flex flex-col">
      <div className="p-6 border-b border-pruno-dark/40">
        <div className="flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-magenta" />
          <h1 className="font-bold text-lg">MBC Decks</h1>
        </div>
        <p className="text-xs text-ceramica/70 mt-1">Generador de presentaciones</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-chamfer transition ${
                active ? 'bg-magenta text-white' : 'hover:bg-pruno-dark text-ceramica/90'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="text-sm">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-pruno-dark/40">
        <div className="text-xs text-ceramica/70 mb-2">{user?.full_name}</div>
        <div className="text-xs text-ceramica/50 mb-3 capitalize">{user?.role}</div>
        <button
          onClick={() => { clearSession(); router.push('/login'); }}
          className="flex items-center gap-2 text-sm text-ceramica/80 hover:text-white"
        >
          <LogOut className="w-4 h-4" /> Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
