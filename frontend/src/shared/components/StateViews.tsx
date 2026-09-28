import { AlertTriangle, Inbox, RotateCcw } from 'lucide-react';
import type { ReactNode } from 'react';

export function LoadingState({ rows = 3 }: { rows?: number }) {
  return <div className="skeleton-stack" aria-label="Загрузка данных">{Array.from({ length: rows }, (_, i) => <div className="skeleton" key={i} />)}</div>;
}

export function ErrorState({ message, traceId, onRetry }: { message: string; traceId?: string; onRetry: () => void }) {
  return <div className="state-view error-state"><AlertTriangle aria-hidden="true" /><h2>Не удалось загрузить данные</h2><p>{message}</p>{traceId && <small>Trace ID: {traceId}</small>}<button className="button secondary" onClick={onRetry}><RotateCcw size={16} />Повторить</button></div>;
}

export function EmptyState({
  title,
  message,
  description = 'Измените фильтры или дождитесь новых данных.',
  action,
}: {
  title?: string;
  message?: string;
  description?: string;
  action?: ReactNode;
}) {
  return <div className="state-view"><Inbox aria-hidden="true" /><h2>{title ?? message ?? 'Данных пока нет'}</h2><p>{description}</p>{action}</div>;
}

