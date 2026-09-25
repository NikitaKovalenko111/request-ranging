import { AlertTriangle, Inbox, RotateCcw } from 'lucide-react';

export function LoadingState({ rows = 3 }: { rows?: number }) {
  return <div className="skeleton-stack" aria-label="Загрузка данных">{Array.from({ length: rows }, (_, i) => <div className="skeleton" key={i} />)}</div>;
}

export function ErrorState({ message, traceId, onRetry }: { message: string; traceId?: string; onRetry: () => void }) {
  return <div className="state-view error-state"><AlertTriangle aria-hidden="true" /><h2>Не удалось загрузить данные</h2><p>{message}</p>{traceId && <small>Trace ID: {traceId}</small>}<button className="button secondary" onClick={onRetry}><RotateCcw size={16} />Повторить</button></div>;
}

export function EmptyState({ title = 'Данных пока нет', description = 'Измените фильтры или дождитесь новых данных.' }: { title?: string; description?: string }) {
  return <div className="state-view"><Inbox aria-hidden="true" /><h2>{title}</h2><p>{description}</p></div>;
}

