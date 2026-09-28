import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Assignment } from '../../../types/assignment';
import { StatusBadge } from '../../../shared/components/StatusBadge';
import { formatDateTime, formatDuration } from '../../../shared/format';

export function LatestAssignmentsTable({ items }: { items: Assignment[] }) {
  return <section className="panel table-panel"><div className="panel-heading"><div><span className="section-kicker">Последние события</span><h2>Назначения</h2></div><Link className="text-link" to="/orders">Все заявки <ArrowUpRight size={15} /></Link></div><div className="table-scroll"><table><thead><tr><th>Время</th><th>Заявка</th><th>Исполнитель</th><th>Статус</th><th>Решение</th><th><span className="sr-only">Действие</span></th></tr></thead><tbody>{items.map((item) => <tr key={item.orderId}><td>{formatDateTime(item.confirmedAt ?? item.createdAt)}</td><td><strong>#{item.orderId}</strong></td><td>{item.executorName ?? 'Не назначен'}</td><td><StatusBadge status={item.status} /></td><td>{formatDuration(item.processingTimeMs)}</td><td><Link className="row-action" to={`/orders/${item.orderId}`} aria-label={`Открыть заявку ${item.orderId}`}><ArrowUpRight size={17} /></Link></td></tr>)}</tbody></table></div></section>;
}

