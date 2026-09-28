import { ArrowRight, Repeat2, Star } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { Order } from '../../../types/order';
import { StatusBadge } from '../../../shared/components/StatusBadge';
import { formatDateTime, formatDuration } from '../../../shared/format';

export function OrdersTable({ items }: { items: Order[] }) {
  const navigate = useNavigate();
  const open = (id: string) => navigate(`/orders/${encodeURIComponent(id)}`);
  return <div className="panel table-panel orders-table"><div className="table-scroll"><table><thead><tr><th>ID</th><th>Создана</th><th>Тип</th><th>Вес</th><th>Статус заявки</th><th>Назначение</th><th>Исполнитель</th><th>Решение</th><th>Повторная</th><th><span className="sr-only">Открыть</span></th></tr></thead><tbody>{items.map((order) => <tr key={order.id} tabIndex={0} role="link" onClick={() => open(order.id)} onKeyDown={(event) => { if (event.key === 'Enter') open(order.id); }}><td><strong>#{order.id}</strong>{order.vip && <Star className="vip-star" size={14} aria-label="VIP" />}</td><td>{formatDateTime(order.createdAt)}</td><td><span className="truncate-cell" title={order.orderType}>{order.orderType}</span></td><td>{order.weight}</td><td><StatusBadge status={order.status} /></td><td><StatusBadge status={order.assignmentStatus} /></td><td>{order.assignedExecutorName ?? 'Не назначен'}</td><td>{formatDuration(order.processingTimeMs)}</td><td>{order.parentId ? <span className="parent-ref"><Repeat2 size={14} />#{order.parentId}</span> : '—'}</td><td><button className="row-action" onClick={(event) => { event.stopPropagation(); open(order.id); }} aria-label={`Открыть заявку ${order.id}`}><ArrowRight size={17} /></button></td></tr>)}</tbody></table></div></div>;
}

