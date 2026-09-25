import { ArrowRight, Construction } from 'lucide-react';
import { Link } from 'react-router-dom';

export function PlaceholderPage({ title }: { title: string }) {
  return <section className="state-view panel placeholder-page"><Construction /><span className="section-kicker">Смежный контур</span><h2>{title}</h2><p>Этот раздел разрабатывается вторым frontend-разработчиком. Маршрут и общая навигация уже готовы для интеграции.</p><Link className="button secondary" to="/dashboard">Вернуться на Dashboard <ArrowRight size={16} /></Link></section>;
}

