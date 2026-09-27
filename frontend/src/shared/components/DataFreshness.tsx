import { RefreshCw } from 'lucide-react';
import { formatDateTime } from '../format';

export function DataFreshness({ updatedAt, fetching }: { updatedAt?: number; fetching: boolean }) {
  return <div className="freshness" aria-live="polite"><RefreshCw size={14} className={fetching ? 'spin' : ''} /><span>{fetching ? 'Обновляем' : 'Обновлено'}{updatedAt ? ` · ${formatDateTime(new Date(updatedAt).toISOString())}` : ''}</span></div>;
}

