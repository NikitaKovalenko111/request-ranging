import { useState } from 'react';
import type { ApiError } from '../../../types/api';
import type { OrderFilters as Filters } from '../../../types/order';
import { DataFreshness } from '../../../shared/components/DataFreshness';
import { EmptyState, ErrorState, LoadingState } from '../../../shared/components/StateViews';
import { OrderFilters } from '../components/OrderFilters';
import { OrdersTable } from '../components/OrdersTable';
import { useOrders } from '../hooks/useOrders';

const initialFilters: Filters = { id: '', status: '', assignmentStatus: '', orderType: '', vip: '', parentOnly: false };

export function OrdersPage() {
  const [filters, setFilters] = useState(initialFilters);
  const query = useOrders(filters);
  const error = query.error as unknown as ApiError | null;
  return <div className="page-stack"><div className="page-actions"><div><h2 className="page-lead">Все входящие заявки</h2><p>Жизненный цикл, назначение и объяснение каждого решения.</p></div><DataFreshness updatedAt={query.dataUpdatedAt || undefined} fetching={query.isFetching} /></div><OrderFilters value={filters} onChange={setFilters} />{query.isLoading ? <LoadingState rows={7} /> : query.isError ? <ErrorState message={error?.message ?? 'Неизвестная ошибка'} traceId={error?.traceId} onRetry={() => void query.refetch()} /> : !query.data?.items.length ? <EmptyState title="Заявки не найдены" description="Попробуйте изменить или сбросить фильтры." /> : <><div className="result-count">Найдено: <strong>{query.data.pagination.total}</strong></div><OrdersTable items={query.data.items} /></>}</div>;
}
