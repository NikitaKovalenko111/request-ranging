import { Switch } from '../../../shared/components/Switch';
import { Button } from '../../../shared/components/Button';
import { RuleHumanReadable } from './RuleHumanReadable';
import type { Rule } from '../../../types/rule';
import type { RuleFieldDefinition } from '../../../types/ruleSchema';

export function RuleTable({
    items,
    orderFields,
    executorFields,
    onToggle,
    onEdit,
    onDelete,
    onTest,
    pendingId,
}: {
    items: Rule[];
    orderFields: RuleFieldDefinition[];
    executorFields: RuleFieldDefinition[];
    onToggle: (r: Rule) => void;
    onEdit: (r: Rule) => void;
    onDelete: (r: Rule) => void;
    onTest: (r: Rule) => void;
    pendingId: string | null;
}) {
    return (
        <section className="panel table-panel">
            <div className="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Приоритет</th>
                            <th>Название</th>
                            <th>Условие</th>
                            <th>Активность</th>
                            <th>Обновлено</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.map((r) => (
                            <tr key={r.id}>
                                <td>
                                    <strong>{r.priority}</strong>
                                </td>
                                <td>
                                    <strong>{r.name}</strong>
                                    {r.description ? <small className="cell-meta">{r.description}</small> : null}
                                </td>
                                <td>
                                    <RuleHumanReadable
                                        rule={r}
                                        orderFields={orderFields}
                                        executorFields={executorFields}
                                    />
                                </td>
                                <td>
                                    <Switch
                                        checked={r.active}
                                        disabled={pendingId === r.id}
                                        onChange={() => onToggle(r)}
                                    />
                                </td>
                                <td>{new Date(r.updatedAt).toLocaleString('ru-RU')}</td>
                                <td>
                                    <Button variant="ghost" onClick={() => onTest(r)}>
                                        Test
                                    </Button>
                                    <Button variant="ghost" onClick={() => onEdit(r)}>
                                        Edit
                                    </Button>
                                    <Button variant="ghost" onClick={() => onDelete(r)}>
                                        Delete
                                    </Button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </section>
    );
}