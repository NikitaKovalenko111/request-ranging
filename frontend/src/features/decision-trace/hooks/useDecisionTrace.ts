import { useQuery } from '@tanstack/react-query';
import { getAssignmentByOrderId } from '../../../api/assignments';
import { env } from '../../../shared/config/env';
import { queryKeys } from '../../../shared/config/queryKeys';

export function useAssignmentDetails(orderId: string) {
  return useQuery({
    queryKey: queryKeys.assignment(orderId),
    queryFn: ({ signal }) => getAssignmentByOrderId(orderId, signal),
    refetchInterval: (query) => {
      const status = query.state.data?.assignment?.status;
      return status === 'pending' || status === 'reserved' ? env.pollIntervalMs : false;
    },
    staleTime: 30_000,
  });
}
