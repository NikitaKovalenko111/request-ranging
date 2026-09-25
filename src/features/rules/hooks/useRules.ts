import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getRules, setRuleActive, testRules } from '../../../api/rules';
import { queryKeys } from '../../../shared/config/queryKeys';

export function useRules() {
  return useQuery({ queryKey: queryKeys.rules, queryFn: ({ signal }) => getRules(signal), staleTime: 30_000 });
}

export function useSetRuleActive() {
  const client = useQueryClient();
  return useMutation({ mutationFn: ({ id, active }: { id: string; active: boolean }) => setRuleActive(id, active), onSuccess: async () => { await Promise.all([client.invalidateQueries({ queryKey: queryKeys.rules }), client.invalidateQueries({ queryKey: ['dashboard'] })]); } });
}

export function useTestRules() {
  return useMutation({ mutationFn: (orderId: number) => testRules(orderId) });
}
