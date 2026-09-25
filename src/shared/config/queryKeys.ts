import type { DashboardFilters, MockScenario } from '../../types/dashboard';
import type { OrderFilters } from '../../types/order';

export const queryKeys = {
  dashboard: (filters: DashboardFilters, scenario: MockScenario) => ['dashboard', filters, scenario] as const,
  metrics: (filters: DashboardFilters) => ['metrics', filters] as const,
  orders: (filters: OrderFilters) => ['orders', filters] as const,
  order: (id: number) => ['orders', id] as const,
  assignment: (orderId: number) => ['assignments', orderId] as const,
  orderOptions: ['orders', 'options'] as const,
  executors: ['executors'] as const,
  rules: ['rules'] as const,
};
