import { useQuery } from '@tanstack/react-query';
import { getAssignment, getDecisionTrace } from '../../../api/assignments';
import { env } from '../../../shared/config/env';
import { queryKeys } from '../../../shared/config/queryKeys';

export function useAssignment(orderId: number) {
  return useQuery({ queryKey: queryKeys.assignment(orderId), queryFn: ({ signal }) => getAssignment(orderId, signal), refetchInterval: env.pollIntervalMs });
}

export function useDecisionTrace(orderId: number, enabled: boolean) {
  return useQuery({ queryKey: queryKeys.decisionTrace(orderId), queryFn: ({ signal }) => getDecisionTrace(orderId, signal), enabled, refetchInterval: enabled ? env.pollIntervalMs : false });
}

