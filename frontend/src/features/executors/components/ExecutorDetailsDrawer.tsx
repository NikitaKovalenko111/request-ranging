import { Drawer } from '../../../shared/components/Drawer';
import { StatusBadge } from '../../../shared/components/StatusBadge';
import { formatNumber } from '../../../shared/format/formatNumber';
import { formatDate } from '../../../shared/format/formatDate';
import type { Executor } from '../../../types/executor';

export function ExecutorDetailsDrawer({
    executor,
    onClose,
}: {
    executor: Executor | null;
    onClose: () => void;
}) {
    const lastAssignmentAt = executor ? formatDate(executor.lastAssignmentAt) : '';
    return (
        <Drawer
            open={!!executor}
            title={executor ? executor.displayName : ''}
            onClose={onClose}
        >
            {executor ? (
                <div className="details-grid compact">
                    <div>
                        <dt>ID</dt>
                        <dd>#{executor.id}</dd>
                    </div>
                    <div>
                        <dt>Статус</dt>
                        <dd>
                            <StatusBadge status={executor.status} />
                        </dd>
                    </div>
                    <div>
                        <dt>Квалификация</dt>
                        <dd>{executor.qualification ?? '—'}</dd>
                    </div>
                    <div>
                        <dt>Вес (capacityWeight)</dt>
                        <dd>{formatNumber(executor.capacityWeight)}</dd>
                    </div>
                    <div>
                        <dt>Confirmed</dt>
                        <dd>{formatNumber(executor.confirmedWeight)}</dd>
                    </div>
                    <div>
                        <dt>Pending</dt>
                        <dd>{formatNumber(executor.pendingWeight)}</dd>
                    </div>
                    <div>
                        <dt>Effective load</dt>
                        <dd>{formatNumber(executor.effectiveLoad)}</dd>
                    </div>
                    <div>
                        <dt>За сутки</dt>
                        <dd>
                            {executor.dailyCount} /{' '}
                            {executor.maxDailyLimit === null ? 'Без ограничений' : executor.maxDailyLimit}
                        </dd>
                    </div>
                    <div>
                        <dt>Последнее назначение</dt>
                        <dd className="assignment-time" title={lastAssignmentAt}>{lastAssignmentAt}</dd>
                    </div>
                    <div style={{ gridColumn: '1 / -1' }}>
                        <dt>Формула</dt>
                        <dd>
                            effectiveLoad = (confirmedWeight + pendingWeight) / capacityWeight = (
                            {formatNumber(executor.confirmedWeight)} + {formatNumber(executor.pendingWeight)}) /{' '}
                            {formatNumber(executor.capacityWeight)} = {formatNumber(executor.effectiveLoad)}
                        </dd>
                    </div>
                </div>
            ) : null}
        </Drawer>
    );
}
