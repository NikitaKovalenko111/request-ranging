import type { OrderFilters } from '../../types/order';

export const queryKeys = {
  dashboard: ['dashboard'] as const,
  orders: (filters: OrderFilters) => ['orders', filters] as const,
  order: (id: number) => ['orders', id] as const,
  assignment: (orderId: number) => ['assignments', orderId] as const,
  decisionTrace: (orderId: number) => ['decision-trace', orderId] as const,
};

