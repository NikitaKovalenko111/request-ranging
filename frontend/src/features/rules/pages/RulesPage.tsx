import { RuleFilters } from '../components/RuleFilters';
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
import { useToast } from '../../../shared/components/Toast';
import { isApiError } from '../../../api/errors';
import type { Rule, RuleDraft } from '../../../types/rule';

export function RulesPage() {
    const [search, setSearch] = useState('');
    const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);
    const [editing, setEditing] = useState<Rule | null>(null);
    const [creating, setCreating] = useState(false);
    const [deleting, setDeleting] = useState<Rule | null>(null);
    const [testing, setTesting] = useState<RuleDraft | null>(null);
    const [formError, setFormError] = useState<string | null>(null);
    const [fieldErrors, setFieldErrors] = useState<Record<string, string> | undefined>();

    const rulesQuery = useRules({ search, active: activeFilter, limit: 50, offset: 0 });
    const schemaQuery = useRuleSchema();
    const createMut = useCreateRule();
    const updateMut = useUpdateRule();
    const patchMut = usePatchRule();
    const deleteMut = useDeleteRule();
    const toast = useToast();

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

    const closeForm = () => {
        setCreating(false);
        setEditing(null);
        setFormError(null);
        setFieldErrors(undefined);
    };

    const handleSubmit = (draft: RuleDraft) => {
        setFormError(null);
        setFieldErrors(undefined);

        const onError = (err: unknown) => {
            if (isApiError(err)) {
                if (err.status === 409) {
                    setFormError('Конфликт версии: правило было изменено. Обновите данные.');
                    toast.show('Конфликт версии', 'error');
                    return;
                }
                if (err.status === 422 || err.status === 400) {
                    setFormError(err.message);
                    setFieldErrors(err.fieldErrors);
                    toast.show('Ошибка валидации', 'error');
                    return;
                }
                setFormError(err.message);
                toast.show(err.message, 'error');
                return;
            }
            setFormError('Не удалось сохранить правило');
            toast.show('Не удалось сохранить правило', 'error');
        };

        if (editing) {
            updateMut.mutate(
                { id: editing.id, draft },
                {
                    onSuccess: () => {
                        closeForm();
                        toast.show('Правило обновлено', 'success');
                    },
                    onError,
                },
            );
        } else {
            createMut.mutate(draft, {
                onSuccess: () => {
                    closeForm();
                    toast.show('Правило создано', 'success');
                },
                onError,
            });
        }
    };

    return (
        <div className="page-stack">
            <div className="page-actions">
                <div>
                    <h2 className="page-lead">Правила</h2>
                    <p>Всего: {items.length}</p>
                </div>
                <div className="action-row">
                    <RuleFilters
                        search={search}
                        onSearchChange={setSearch}
                        active={activeFilter}
                        onActiveChange={setActiveFilter}
                    />
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
                    onToggle={(r) =>
                        patchMut.mutate(
                            { id: r.id, patch: { active: !r.active } },
                            {
                                onSuccess: () =>
                                    toast.show(
                                        r.active ? 'Правило выключено' : 'Правило включено',
                                        'success',
                                    ),
                                onError: () => toast.show('Не удалось изменить правило', 'error'),
                            },
                        )
                    }
                    onEdit={(r) => setEditing(r)}
                    onDelete={(r) => setDeleting(r)}
                    onTest={(r) => setTesting(r)}
                    onPriorityChange={(r, priority) =>
                        patchMut.mutate(
                            { id: r.id, patch: { priority } },
                            {
                                onSuccess: () => toast.show('Приоритет обновлён', 'success'),
                                onError: () => toast.show('Не удалось изменить приоритет', 'error'),
                            },
                        )
                    }
                    pendingId={patchMut.isPending ? patchMut.variables?.id ?? null : null}
                />
            )}

            <Dialog
                open={creating || !!editing}
                title={editing ? 'Редактировать правило' : 'Новое правило'}
                onClose={closeForm}
            >
                {formError ? (
                    <div className="form-error" role="alert" style={{ marginBottom: 12 }}>
                        {formError}
                    </div>
                ) : null}
                <RuleForm
                    schema={schema}
                    initial={editing ?? undefined}
                    loading={createMut.isPending || updateMut.isPending}
                    onCancel={closeForm}
                    onSubmit={handleSubmit}
                    serverFieldErrors={fieldErrors}
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
                        deleteMut.mutate(deleting.id, {
                            onSettled: () => setDeleting(null),
                            onSuccess: () => toast.show('Правило удалено', 'success'),
                            onError: () => toast.show('Не удалось удалить правило', 'error'),
                        });
                    }
                }}
            />
        </div>
    );
}