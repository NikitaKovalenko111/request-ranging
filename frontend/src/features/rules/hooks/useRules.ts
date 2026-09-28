import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getRules,
  getRuleSchema,
  createRule,
  updateRule,
  patchRule,
  deleteRule,
  testRule,
} from '../../../api/rules';
import { queryKeys } from '../../../api/queryKeys';
import type { RuleDraft, RuleFilters, TestRuleRequest } from '../../../types/rule';

export function useRules(filters: RuleFilters) {
  return useQuery({
    queryKey: queryKeys.rules.list(filters),
    queryFn: ({ signal }) => getRules(filters, signal),
  });
}

export function useRuleSchema() {
  return useQuery({
    queryKey: queryKeys.rules.schema,
    queryFn: ({ signal }) => getRuleSchema({ signal }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (draft: RuleDraft) => createRule(draft),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.rules.all });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}

export function useUpdateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, draft }: { id: string; draft: RuleDraft }) => updateRule(id, draft),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.rules.all });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}

export function usePatchRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: { active?: boolean; priority?: number } }) =>
      patchRule(id, patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.rules.all });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteRule(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.rules.all });
      qc.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}

export function useTestRule() {
  return useMutation({
    mutationFn: (request: TestRuleRequest) => testRule(request),
  });
}