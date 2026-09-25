import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import type { ApiError } from '../../../types/api';
import type { OrderFilters as Filters } from '../../../types/order';
import { DataFreshness } from '../../../shared/components/DataFreshness';
import { EmptyState, ErrorState, LoadingState } from '../../../shared/components/StateViews';
import { useExecutors } from '../../executors/hooks/useExecutors';
import { emptyOrderFilters, OrderFilters } from '../components/OrderFilters';
import { OrdersTable } from '../components/OrdersTable';
import { useOrders } from '../hooks/useOrders';

function readFilters(params: URLSearchParams): Filters {
  const limit = Number(params.get('limit'));
  const offset = Number(params.get('offset'));
  return {
    ...emptyOrderFilters,
    search: params.get('search') ?? '',
    status: (params.get('status') ?? '') as Filters['status'],
    assignmentStatus: (params.get('assignmentStatus') ?? '') as Filters['assignmentStatus'],
    orderType: params.get('orderType') ?? '',
    vip: (params.get('vip') ?? '') as Filters['vip'],
    hasParent: params.get('hasParent') === 'true',
    executorId: params.get('executorId') ?? '',
    from: params.get('from') ?? '',
    to: params.get('to') ?? '',
    limit: [5, 10, 20].includes(limit) ? limit : 5,
    offset: Number.isFinite(offset) && offset >= 0 ? offset : 0,
    sort: (params.get('sort') ?? 'createdAt') as Filters['sort'],
    order: (params.get('order') ?? 'desc') as Filters['order'],
  };
}

function writeFilters(filters: Filters): URLSearchParams {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== '' && value !== false && !(key === 'offset' && value === 0) && !(key === 'limit' && value === 5) && !(key === 'sort' && value === 'createdAt') && !(key === 'order' && value === 'desc')) params.set(key, String(value));
  });
  return params;
}

export function OrdersPage() {
  const [params, setParams] = useSearchParams();
  const filters = readFilters(params);
  const query = useOrders(filters);
  const executorsQuery = useExecutors();
  const error = query.error as unknown as ApiError | null;
  const total = query.data?.pagination.total ?? 0;
  const page = Math.floor(filters.offset / filters.limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / filters.limit));
  const update = (next: Filters) => setParams(writeFilters(next), { replace: true });
  const executors = (executorsQuery.data ?? []).map((item) => ({ id: item.id, name: item.displayName }));

  return <div className="page-stack">
    <div className="page-actions"><div><h2 className="page-lead">Все входящие заявки</h2><p>Жизненный цикл, назначение и объяснение каждого решения.</p></div><DataFreshness updatedAt={query.dataUpdatedAt || undefined} fetching={query.isFetching} /></div>
    <OrderFilters value={filters} executors={executors} onChange={update} />
    {query.isLoading ? <LoadingState rows={7} /> : query.isError ? <ErrorState message={error?.message ?? 'Неизвестная ошибка'} traceId={error?.traceId} onRetry={() => void query.refetch()} /> : !query.data?.items.length ? <EmptyState title="Заявки не найдены" description="Попробуйте изменить или сбросить фильтры." /> : <><div className="results-toolbar"><div className="result-count">Найдено: <strong>{total}</strong></div><label>Строк на странице <select value={filters.limit} onChange={(event) => update({ ...filters, limit: Number(event.target.value), offset: 0 })}><option value={5}>5</option><option value={10}>10</option><option value={20}>20</option></select></label></div><OrdersTable items={query.data.items} /><nav className="pagination" aria-label="Пагинация"><button className="button secondary" disabled={page === 1} onClick={() => update({ ...filters, offset: Math.max(0, filters.offset - filters.limit) })}><ChevronLeft size={16} />Назад</button><span>Страница <strong>{page}</strong> из {pageCount}</span><button className="button secondary" disabled={page >= pageCount} onClick={() => update({ ...filters, offset: filters.offset + filters.limit })}>Вперёд<ChevronRight size={16} /></button></nav></>}
  </div>;
}
