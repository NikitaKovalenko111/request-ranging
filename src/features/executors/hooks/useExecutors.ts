import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getExecutors, updateExecutor } from '../../../api/executors';
import { queryKeys } from '../../../api/queryKeys';
import { POLL_INTERVAL_MS } from '../../../api/dataSource';
import type { ExecutorFilters, UpdateExecutorRequest } from '../../../types/executor';

export function useExecutors(filters: ExecutorFilters) {
  return useQuery({
    queryKey: queryKeys.executors.list(filters),
    queryFn: ({ signal }) => getExecutors(filters, signal),
    refetchInterval: POLL_INTERVAL_MS,
  });
}

export function useUpdateExecutor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: UpdateExecutorRequest }) =>
      updateExecutor(id, patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.executors.all });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}
