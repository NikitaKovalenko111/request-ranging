import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { getDashboard } from '../../../api/dashboard';
import { env } from '../../../shared/config/env';
import { queryKeys } from '../../../shared/config/queryKeys';

export function useDashboard() {
  return useQuery({ queryKey: queryKeys.dashboard, queryFn: ({ signal }) => getDashboard(signal), refetchInterval: env.pollIntervalMs, placeholderData: keepPreviousData });
}

