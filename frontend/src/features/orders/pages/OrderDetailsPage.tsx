import { ArrowLeft, ArrowUpRight, Crown, GitBranch } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import type { ApiError } from '../../../types/api';
import { EmptyState, ErrorState, LoadingState } from '../../../shared/components/StateViews';
import { StatusBadge } from '../../../shared/components/StatusBadge';
import { formatDateTime, formatDuration, formatMoney } from '../../../shared/format';
import { DecisionTraceView } from '../../decision-trace/components/DecisionTraceView';
import { useAssignmentDetails } from '../../decision-trace/hooks/useDecisionTrace';
import { useOrder } from '../hooks/useOrders';

export function OrderDetailsPage() {
  const id = useParams().id ?? '';
  const orderQuery = useOrder(id);
  const assignmentQuery = useAssignmentDetails(id);
  if (!id) return <EmptyState title="Некорректный ID заявки" />;
  if (orderQuery.isLoading) return <LoadingState rows={5} />;
  if (orderQuery.isError) { const error = orderQuery.error as unknown as ApiError; return <ErrorState message={error.message ?? 'Неизвестная ошибка'} traceId={error.traceId} onRetry={() => void orderQuery.refetch()} />; }
  const order = orderQuery.data!;
  const assignedAt = formatDateTime(order.assignedAt);
  return <div className="page-stack"><div className="details-header"><Link className="back-link" to="/orders"><ArrowLeft size={17} />К списку</Link><div className="details-title"><div><span className="section-kicker">Заявка</span><h2>#{order.id} {order.vip && <span className="vip-label"><Crown size={15} />VIP</span>}</h2></div><div className="status-group"><StatusBadge status={order.status} /><StatusBadge status={order.assignmentStatus} /></div></div></div>
    <section className="panel order-overview"><div className="panel-heading"><div><span className="section-kicker">Параметры</span><h2>{order.orderType}</h2></div><span className="order-weight">Вес {order.weight}</span></div><dl className="details-grid"><div><dt>Сумма</dt><dd>{formatMoney(order.sum)}</dd></div><div><dt>Тематика</dt><dd>{order.subject}</dd></div><div><dt>Клиент МСП</dt><dd>{order.clientMsp ?? 'Не указано'}</dd></div><div><dt>Исполнитель МСП</dt><dd>{order.executorMsp ?? 'Не указано'}</dd></div><div><dt>Создана</dt><dd>{formatDateTime(order.createdAt)}</dd></div><div><dt>Назначена</dt><dd className="assignment-time" title={assignedAt}>{assignedAt}</dd></div><div><dt>Время решения</dt><dd>{formatDuration(order.processingTimeMs)}</dd></div><div><dt>Исполнитель</dt><dd>{order.assignedExecutorName ?? 'Не назначен'}</dd></div></dl><div className="order-text"><span>Текст заявки</span><p>{order.text}</p></div>{order.parentId && <Link className="parent-link" to={`/orders/${order.parentId}`}><GitBranch size={17} /><span>Родительская заявка <strong>#{order.parentId}</strong></span><ArrowUpRight size={16} /></Link>}</section>
    {assignmentQuery.isLoading ? <LoadingState rows={2} /> : assignmentQuery.isError ? <ErrorState message={(assignmentQuery.error as unknown as ApiError).message ?? 'Не удалось получить назначение'} onRetry={() => void assignmentQuery.refetch()} /> : assignmentQuery.data?.assignment?.status === 'pending' || assignmentQuery.data?.assignment?.status === 'reserved' ? <section className="panel pending-panel"><span className="pulse-ring" /><div><h2>Назначение ещё обрабатывается</h2><p>{assignmentQuery.data.assignment.explanation ?? 'Ожидаем результат резервирования исполнителя.'}</p></div></section> : assignmentQuery.data?.decisionTrace ? <DecisionTraceView trace={assignmentQuery.data.decisionTrace} /> : <EmptyState title="Decision Trace недоступен" description="Backend не вернул трассу решения для этой заявки." />}
  </div>;
}
