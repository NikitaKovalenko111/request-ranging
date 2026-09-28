import { apiClient } from './client';
import { useMockData } from './dataSource';
import { mockRules } from '../mocks/rules';
import { mockRuleSchema } from '../mocks/ruleSchema';
import type { Rule, RuleDraft, RuleFilters, TestRuleRequest, TestRuleResponse } from '../types/rule';
import type { RuleSchema } from '../types/ruleSchema';
import type { PaginatedResponse, RequestOptions } from '../types/api';

let inMemory: Rule[] = [...mockRules];
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function getRuleSchema(options?: RequestOptions): Promise<RuleSchema> {
  if (useMockData) {
    await delay(200);
    return mockRuleSchema;
  }
  return apiClient.get('/rule-schema', options);
}

export async function getRules(
  filters: RuleFilters,
  signal?: AbortSignal,
): Promise<PaginatedResponse<Rule>> {
  if (useMockData) {
    await delay(300);
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    let result = [...inMemory];
    if (filters.active !== undefined) result = result.filter((r) => r.active === filters.active);
    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter((r) => r.name.toLowerCase().includes(q));
    }
    result.sort((a, b) => a.priority - b.priority);
    const offset = filters.offset ?? 0;
    const limit = filters.limit ?? 50;
    return {
      items: result.slice(offset, offset + limit),
      pagination: { limit, offset, total: result.length },
    };
  }
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') params.append(k, String(v));
  });
  return apiClient.get(`/rules?${params.toString()}`, { signal });
}

export async function createRule(draft: RuleDraft): Promise<Rule> {
  if (useMockData) {
    await delay(300);
    const now = new Date().toISOString();
    const created: Rule = {
      ...draft,
      id: `rule-${Date.now()}`,
      createdAt: now,
      updatedAt: now,
      version: 1,
    };
    inMemory = [...inMemory, created];
    return created;
  }
  return apiClient.post('/rules', draft);
}

export async function updateRule(id: string, draft: RuleDraft): Promise<Rule> {
  if (useMockData) {
    await delay(300);
    const idx = inMemory.findIndex((r) => r.id === id);
    if (idx === -1) throw new Error('Rule not found');
    const updated: Rule = {
      ...inMemory[idx],
      ...draft,
      updatedAt: new Date().toISOString(),
      version: (inMemory[idx].version ?? 1) + 1,
    };
    inMemory[idx] = updated;
    return updated;
  }
  return apiClient.put(`/rules/${id}`, draft);
}

export async function patchRule(
  id: string,
  patch: Partial<Pick<Rule, 'active' | 'priority'>>,
): Promise<Rule> {
  if (useMockData) {
    await delay(200);
    const idx = inMemory.findIndex((r) => r.id === id);
    if (idx === -1) throw new Error('Rule not found');
    inMemory[idx] = { ...inMemory[idx], ...patch, updatedAt: new Date().toISOString() };
    return inMemory[idx];
  }
  return apiClient.patch(`/rules/${id}`, patch);
}

export async function deleteRule(id: string): Promise<void> {
  if (useMockData) {
    await delay(200);
    inMemory = inMemory.filter((r) => r.id !== id);
    return;
  }
  await apiClient.delete(`/rules/${id}`);
}

export async function testRule(request: TestRuleRequest): Promise<TestRuleResponse> {
  if (useMockData) {
    await delay(400);
    const passed = Math.random() > 0.4;
    return {
      result: passed ? 'PASS' : 'FAIL',
      reason: passed
        ? 'Все условия правила выполнены'
        : 'Квалификация исполнителя не соответствует требованию',
      comparisons: [
        {
          leftField: 'vip',
          leftValue: true,
          operator: 'EQ',
          rightSource: 'CONSTANT',
          rightValue: true,
        },
      ],
    };
  }
  return apiClient.post('/rules/test', request);
}