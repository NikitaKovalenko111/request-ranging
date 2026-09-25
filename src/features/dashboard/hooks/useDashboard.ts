import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { getDashboard } from '../../../api/dashboard';
import { env } from '../../../shared/config/env';
import { queryKeys } from '../../../shared/config/queryKeys';
import type { DashboardFilters, MockScenario } from '../../../types/dashboard';

export function useDashboard(filters: DashboardFilters, scenario: MockScenario) {
  return useQuery({ queryKey: queryKeys.dashboard(filters, scenario), queryFn: ({ signal }) => getDashboard(filters, scenario, signal), refetchInterval: env.pollIntervalMs, placeholderData: keepPreviousData });
}
