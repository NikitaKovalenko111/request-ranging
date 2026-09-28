import type { ExecutorFilters } from '../types/executor';
import type { RuleFilters } from '../types/rule';

export const queryKeys = {
    executors: {
        all: ['executors'] as const,
        list: (filters: ExecutorFilters) => ['executors', 'list', filters] as const,
        detail: (id: string) => ['executors', 'detail', id] as const,
    },
    rules: {
        all: ['rules'] as const,
        list: (filters: RuleFilters) => ['rules', 'list', filters] as const,
        schema: ['rules', 'schema'] as const,
    },
    orders: {
        options: ['orders', 'options'] as const,
    },
    dashboard: {
        all: ['dashboard'] as const,
    },
};