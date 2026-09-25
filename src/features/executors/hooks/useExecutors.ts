import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getExecutors, setExecutorStatus } from '../../../api/executors';
import { queryKeys } from '../../../shared/config/queryKeys';

export function useExecutors() {
  return useQuery({ queryKey: queryKeys.executors, queryFn: ({ signal }) => getExecutors(signal), staleTime: 30_000 });
}

export function useSetExecutorStatus() {
  const client = useQueryClient();
  return useMutation({ mutationFn: ({ id, status }: { id: number; status: 'ACTIVE' | 'INACTIVE' }) => setExecutorStatus(id, status), onSuccess: async () => { await Promise.all([client.invalidateQueries({ queryKey: queryKeys.executors }), client.invalidateQueries({ queryKey: ['dashboard'] })]); } });
}
