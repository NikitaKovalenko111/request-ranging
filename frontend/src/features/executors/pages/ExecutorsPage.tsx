import { useState } from 'react';
import { useExecutors, useUpdateExecutor } from '../hooks/useExecutors';
import { ExecutorTable } from '../components/ExecutorTable';
import { ConfirmDialog } from '../../../shared/components/ConfirmDialog';
import { LoadingState, ErrorState, EmptyState } from '../../../shared/components/StateViews';
import { Input } from '../../../shared/components/Input';
import { Select } from '../../../shared/components/Select';
import type { Executor, ExecutorFilters } from '../../../types/executor';

export function ExecutorsPage() {
  const [filters, setFilters] = useState<ExecutorFilters>({ limit: 20, offset: 0 });
  const [confirm, setConfirm] = useState<Executor | null>(null);
  const { data, isLoading, isError, refetch } = useExecutors(filters);
  const mutation = useUpdateExecutor();

  if (isLoading) return <LoadingState />;
  if (isError) {
    return (
      <ErrorState
        message="Не удалось загрузить исполнителей"
        onRetry={() => void refetch()}
      />
    );
  }

  const items = data?.items ?? [];
  const activeCount = items.filter((e) => e.status === 'ACTIVE').length;

  const handleToggle = (e: Executor) => {
    if (e.status === 'ACTIVE') setConfirm(e);
    else mutation.mutate({ id: e.id, patch: { status: 'ACTIVE' } });
  };

  return (
    <div className="page-stack">
      <div className="page-actions">
        <div>
          <h2 className="page-lead">Исполнители</h2>
          <p>Активных: {activeCount} из {items.length}</p>
        </div>
        <div className="action-row">
          <Input
            placeholder="Поиск по ФИО"
            onChange={(ev) =>
              setFilters((f) => ({ ...f, search: ev.target.value, offset: 0 }))
            }
          />
          <Select
            value={filters.status ?? ''}
            onChange={(ev) =>
              setFilters((f) => ({
                ...f,
                status: (ev.target.value || undefined) as ExecutorFilters['status'],
                offset: 0,
              }))
            }
          >
            <option value="">Все</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="INACTIVE">INACTIVE</option>
          </Select>
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState message="Исполнители не найдены" />
      ) : (
        <ExecutorTable
          items={items}
          onToggle={handleToggle}
          pendingId={mutation.isPending ? mutation.variables?.id ?? null : null}
        />
      )}

      <ConfirmDialog
        open={!!confirm}
        title="Отключить исполнителя?"
        message={confirm ? `Перевести ${confirm.displayName} в INACTIVE?` : ''}
        loading={mutation.isPending}
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm) {
            mutation.mutate(
              { id: confirm.id, patch: { status: 'INACTIVE' } },
              { onSettled: () => setConfirm(null) },
            );
          }
        }}
      />
    </div>
  );
}