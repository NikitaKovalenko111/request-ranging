import { Activity, Gauge, Power } from 'lucide-react';
import type { ApiError } from '../../../types/api';
import { ErrorState, LoadingState } from '../../../shared/components/StateViews';
import { StatusBadge } from '../../../shared/components/StatusBadge';
import { formatNumber } from '../../../shared/format';
import { useExecutors, useSetExecutorStatus } from '../hooks/useExecutors';

export function ExecutorsPage() {
  const query = useExecutors();
  const mutation = useSetExecutorStatus();
  if (query.isLoading) return <LoadingState rows={5} />;
  if (query.isError) return <ErrorState message={(query.error as unknown as ApiError).message} onRetry={() => void query.refetch()} />;
  const items = query.data ?? [];
  return <div className="page-stack"><div className="page-actions"><div><h2 className="page-lead">Исполнители</h2><p>Активность, квалификация, лимиты и текущая взвешенная нагрузка.</p></div><span className="summary-chip"><Activity size={16} />Активны {items.filter((item) => item.status === 'ACTIVE').length} из {items.length}</span></div><section className="panel table-panel"><div className="table-scroll"><table><thead><tr><th>Исполнитель</th><th>Статус</th><th>Квалификация</th><th>Capacity</th><th>Confirmed</th><th>Pending</th><th>Effective</th><th>Лимит</th><th>Действие</th></tr></thead><tbody>{items.map((executor) => <tr key={executor.id}><td><strong>{executor.displayName}</strong><small className="cell-meta">#{executor.id}</small></td><td><StatusBadge status={executor.status} /></td><td>{executor.qualification ?? 'Не указана'}</td><td>{formatNumber(executor.capacityWeight)}</td><td>{formatNumber(executor.confirmedWeight)}</td><td>{formatNumber(executor.pendingWeight)}</td><td><strong><Gauge size={14} /> {formatNumber(executor.effectiveLoad)}</strong></td><td>{executor.dailyCount} / {executor.maxDailyLimit ?? '∞'}</td><td><button className="button secondary compact-button" disabled={mutation.isPending} onClick={() => mutation.mutate({ id: executor.id, status: executor.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE' })}><Power size={14} />{executor.status === 'ACTIVE' ? 'Отключить' : 'Включить'}</button></td></tr>)}</tbody></table></div></section></div>;
}

