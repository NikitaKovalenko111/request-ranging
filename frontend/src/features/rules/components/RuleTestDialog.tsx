import { useState } from 'react';
import { Dialog } from '../../../shared/components/Dialog';
import { Button } from '../../../shared/components/Button';
import { Input } from '../../../shared/components/Input';
import { useTestRule } from '../hooks/useRules';
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
    const [orderId, setOrderId] = useState('1032');
    const [executorId, setExecutorId] = useState('28');
    const [result, setResult] = useState<TestRuleResponse | null>(null);
    const testMut = useTestRule();

    if (!rule) return null;

    return (
        <Dialog open={open} title="Тестирование правила" onClose={onClose}>
            <Input
                type="text"
                value={orderId}
                onChange={(e) => setOrderId(e.target.value)}
                placeholder="Order ID"
            />
            <Input
                type="text"
                value={executorId}
                onChange={(e) => setExecutorId(e.target.value)}
                placeholder="Executor ID"
            />
            <Button
                loading={testMut.isPending}
                disabled={!orderId || !executorId}
                onClick={() =>
                    testMut.mutate({ rule, orderId, executorId }, { onSuccess: setResult })
                }
            >
                Проверить
            </Button>

            {result && (
                <div className={`test-result test-${result.result.toLowerCase()}`}>
                    <strong>{result.result === 'PASS' ? '✓ PASS' : '✕ FAIL'}</strong>
                    <p>{result.reason}</p>
                    <ul>
                        {result.comparisons.map((c, i) => (
                            <li key={i}>
                                {c.leftField} ({String(c.leftValue)}) {c.operator}{' '}
                                {String(c.rightValue)}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </Dialog>
    );
}
