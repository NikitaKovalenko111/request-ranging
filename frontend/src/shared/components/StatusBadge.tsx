import type { AssignmentStatus, OrderStatus } from '../../types/order';

type Status = AssignmentStatus | OrderStatus | 'ACTIVE' | 'INACTIVE' | 'SUCCESS' | 'CONFLICT' | 'SKIPPED';

const labels: Record<Status, string> = {
  processed: 'Обработана', await: 'Ожидает', accept: 'Принята', reject: 'Отклонена',
  pending: 'Ожидание', reserved: 'Резерв', assigned: 'Назначена', unassigned: 'Не назначена', failed: 'Ошибка',
  ACTIVE: 'Активен', INACTIVE: 'Неактивен', SUCCESS: 'Успех', CONFLICT: 'Конфликт', SKIPPED: 'Пропущено',
};

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`status-badge status-${status.toLowerCase()}`}>{labels[status]}</span>;
}

