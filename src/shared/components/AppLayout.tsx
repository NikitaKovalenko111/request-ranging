import { useState } from 'react';
import { Activity, ClipboardList, Gauge, Menu, Scale, Settings2, X } from 'lucide-react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

const links = [
  { to: '/dashboard', label: 'Dashboard', icon: Gauge },
  { to: '/orders', label: 'Заявки', icon: ClipboardList },
  { to: '/executors', label: 'Исполнители', icon: Activity },
  { to: '/rules', label: 'Правила', icon: Settings2 },
];

const titles: Record<string, string> = { '/dashboard': 'Обзор системы', '/orders': 'Заявки', '/executors': 'Исполнители', '/rules': 'Правила' };

export function AppLayout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const title = location.pathname.startsWith('/orders/') ? 'Детали заявки' : (titles[location.pathname] ?? 'Executor Balancer');
  return <div className="app-shell">
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="brand"><span className="brand-mark"><Scale size={21} /></span><span><strong>Executor</strong><small>Balancer</small></span><button className="icon-button close-nav" onClick={() => setOpen(false)} aria-label="Закрыть меню"><X /></button></div>
      <nav aria-label="Основная навигация">{links.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} onClick={() => setOpen(false)}><Icon size={19} /><span>{label}</span></NavLink>)}</nav>
      <div className="sidebar-footer"><span className="live-dot" />Mock поток активен<small>Polling каждые 2 сек.</small></div>
    </aside>
    {open && <button className="backdrop" onClick={() => setOpen(false)} aria-label="Закрыть меню" />}
    <div className="main-column">
      <header className="topbar"><button className="icon-button menu-button" onClick={() => setOpen(true)} aria-label="Открыть меню"><Menu /></button><div><span className="eyebrow">Контур мониторинга</span><h1>{title}</h1></div><div className="system-health"><span className="live-dot" />Система работает</div></header>
      <main><Outlet /></main>
    </div>
  </div>;
}

