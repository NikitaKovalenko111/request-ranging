import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return <div className="not-found"><span>404</span><h1>Такой страницы нет</h1><p>Проверьте адрес или вернитесь к мониторингу.</p><Link className="button primary" to="/dashboard"><ArrowLeft size={16} />На Dashboard</Link></div>;
}

