import { useState } from 'react';
import {
  useRules,
  useRuleSchema,
  useCreateRule,
  useUpdateRule,
  usePatchRule,
  useDeleteRule,
} from '../hooks/useRules';
import { RuleTable } from '../components/RuleTable';
import { RuleForm } from '../components/RuleForm';
import { RuleTestDialog } from '../components/RuleTestDialog';
import { Dialog } from '../../../shared/components/Dialog';
import { ConfirmDialog } from '../../../shared/components/ConfirmDialog';
import { LoadingState, ErrorState, EmptyState } from '../../../shared/components/StateViews';
import { Button } from '../../../shared/components/Button';
import { Input } from '../../../shared/components/Input';
import type { Rule, RuleDraft } from '../../../types/rule';

export function RulesPage() {
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);
  const [editing, setEditing] = useState<Rule | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<Rule | null>(null);
  const [testing, setTesting] = useState<RuleDraft | null>(null);

  const rulesQuery = useRules({ search, active: activeFilter, limit: 50, offset: 0 });
  const schemaQuery = useRuleSchema();
  const createMut = useCreateRule();
  const updateMut = useUpdateRule();
  const patchMut = usePatchRule();
  const deleteMut = useDeleteRule();

  if (rulesQuery.isLoading || schemaQuery.isLoading) return <LoadingState />;

  if (rulesQuery.isError || schemaQuery.isError) {
    return (
      <ErrorState
        message="Не удалось загрузить правила"
        onRetry={() => void rulesQuery.refetch()}
      />
    );
  }

  const schema = schemaQuery.data!;
  const items = rulesQuery.data?.items ?? [];

  return (
    <div className="page-stack">
      <div className="page-actions">
        <div>
          <h2 className="page-lead">Правила</h2>
          <p>Всего: {items.length}</p>
        </div>
        <div className="action-row">
          <Input
            placeholder="Поиск"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            value={String(activeFilter ?? '')}
            onChange={(e) =>
              setActiveFilter(
                e.target.value === '' ? undefined : e.target.value === 'true',
              )
            }
          >
            <option value="">Все</option>
            <option value="true">Активные</option>
            <option value="false">Неактивные</option>
          </select>
          <Button onClick={() => setCreating(true)}>Создать</Button>
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState
          message="Правил нет"
          action={<Button onClick={() => setCreating(true)}>Создать</Button>}
        />
      ) : (
        <RuleTable
          items={items}
          orderFields={schema.orderFields}
          executorFields={schema.executorFields}
          onToggle={(r) => patchMut.mutate({ id: r.id, patch: { active: !r.active } })}
          onEdit={(r) => setEditing(r)}
          onDelete={(r) => setDeleting(r)}
          onTest={(r) => setTesting(r)}
          pendingId={patchMut.isPending ? patchMut.variables?.id ?? null : null}
        />
      )}

      <Dialog
        open={creating || !!editing}
        title={editing ? 'Редактировать правило' : 'Новое правило'}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
      >
        <RuleForm
          schema={schema}
          initial={editing ?? undefined}
          loading={createMut.isPending || updateMut.isPending}
          onCancel={() => {
            setCreating(false);
            setEditing(null);
          }}
          onSubmit={(draft) => {
            if (editing) {
              updateMut.mutate(
                { id: editing.id, draft },
                { onSuccess: () => setEditing(null) },
              );
            } else {
              createMut.mutate(draft, { onSuccess: () => setCreating(false) });
            }
          }}
        />
      </Dialog>

      <RuleTestDialog
        open={!!testing}
        rule={testing}
        onClose={() => setTesting(null)}
      />

      <ConfirmDialog
        open={!!deleting}
        title="Удалить правило?"
        message={deleting ? `Правило "${deleting.name}" будет удалено` : ''}
        loading={deleteMut.isPending}
        onCancel={() => setDeleting(null)}
        onConfirm={() => {
          if (deleting) {
            deleteMut.mutate(deleting.id, { onSettled: () => setDeleting(null) });
          }
        }}
      />
    </div>
  );
}