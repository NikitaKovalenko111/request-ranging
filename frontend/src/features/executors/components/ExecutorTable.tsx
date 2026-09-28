import { Switch } from '../../../shared/components/Switch';
import { StatusBadge } from '../../../shared/components/StatusBadge';
import type { Executor } from '../../../types/executor';

function formatLimit(e: Executor): string {
    return e.maxDailyLimit === null
        ? `${e.dailyCount} / Без ограничений`
        : `${e.dailyCount} / ${e.maxDailyLimit}`;
}

export function ExecutorTable({
    items,
    onToggle,
    pendingId,
}: {
    items: Executor[];
    onToggle: (e: Executor) => void;
    pendingId: string | null;
}) {
    return (
        <section className="panel table-panel">
            <div className="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Исполнитель</th>
                            <th>Статус</th>
                            <th>Квалификация</th>
                            <th>Вес</th>
                            <th>Confirmed</th>
                            <th>Pending</th>
                            <th>Effective load</th>
                            <th>За сутки</th>
                            <th>Последнее назначение</th>
                            <th>Действие</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.map((e) => (
                            <tr key={e.id}>
                                <td>
                                    <strong>{e.displayName}</strong>
                                    <small className="cell-meta">#{e.id}</small>
                                </td>
                                <td>
                                    <StatusBadge status={e.status} />
                                </td>
                                <td>{e.qualification ?? '—'}</td>
                                <td>{e.capacityWeight}</td>
                                <td>{e.confirmedWeight}</td>
                                <td>{e.pendingWeight}</td>
                                <td>
                                    <strong>{e.effectiveLoad}</strong>
                                </td>
                                <td>{formatLimit(e)}</td>
                                <td>
                                    {e.lastAssignmentAt
                                        ? new Date(e.lastAssignmentAt).toLocaleString('ru-RU')
                                        : '—'}
                                </td>
                                <td>
                                    <Switch
                                        checked={e.status === 'ACTIVE'}
                                        disabled={pendingId === e.id}
                                        onChange={() => onToggle(e)}
                                    />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </section>
    );
}
