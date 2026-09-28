import { useState } from 'react';
import { Dialog } from '../../../shared/components/Dialog';
import { Button } from '../../../shared/components/Button';
import { Select } from '../../../shared/components/Select';
import { FormField } from '../../../shared/components/form/FormField';
import { useTestRule } from '../hooks/useRules';
import { useOrderOptions } from '../hooks/useOrderOptions';
import { useExecutors } from '../../executors/hooks/useExecutors';
import type { RuleDraft, TestRuleResponse } from '../../../types/rule';

export function RuleTestDialog({
    open,
    rule,
    onClose,
}: {
    open: boolean;
    rule: RuleDraft | null;
    onClose: () => void;
}) {
    const ordersQuery = useOrderOptions();
    const executorsQuery = useExecutors({ limit: 100, offset: 0 });
    const [orderId, setOrderId] = useState<number | null>(null);
    const [executorId, setExecutorId] = useState<number | null>(null);
    const [result, setResult] = useState<TestRuleResponse | null>(null);
    const testMut = useTestRule();

    if (!rule) return null;

    const orders = ordersQuery.data ?? [];
    const executors = executorsQuery.data?.items ?? [];

    const canSubmit = orderId !== null && executorId !== null && !testMut.isPending;

    return (
        <Dialog open={open} title="Тестирование правила" onClose={onClose}>
            <FormField label="Заявка" required>
                <Select
                    value={orderId === null ? '' : String(orderId)}
                    onChange={(e) => setOrderId(e.target.value === '' ? null : Number(e.target.value))}
                >
                    <option value="">— выберите заявку —</option>
                    {orders.map((o) => (
                        <option key={o.id} value={o.id}>
                            {o.label}
                        </option>
                    ))}
                </Select>
            </FormField>

            <FormField label="Исполнитель" required>
                <Select
                    value={executorId === null ? '' : String(executorId)}
                    onChange={(e) => setExecutorId(e.target.value === '' ? null : Number(e.target.value))}
                >
                    <option value="">— выберите исполнителя —</option>
                    {executors.map((ex) => (
                        <option key={ex.id} value={ex.id}>
                            {ex.displayName} ({ex.qualification ?? '—'})
                        </option>
                    ))}
                </Select>
            </FormField>

            <Button
                loading={testMut.isPending}
                disabled={!canSubmit}
                onClick={() => {
                    if (orderId === null || executorId === null) return;
                    testMut.mutate({ rule, orderId, executorId }, { onSuccess: setResult });
                }}
            >
                Проверить
            </Button>

            {result && (
                <div className={`test-result ${result.result === 'PASS' ? 'test-pass' : 'test-fail'}`}>
                    <strong>{result.result === 'PASS' ? '✓ PASS' : '✕ FAIL'}</strong>
                    <p>{result.reason}</p>
                    <ul>
                        {result.comparisons.map((c, i) => (
                            <li key={i}>
                                {c.leftField} ({String(c.leftValue)}) {c.operator} {String(c.rightValue)}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </Dialog>
    );
}