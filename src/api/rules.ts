import type { RuleSummary } from '../types/rule';
import { mockRules } from '../mocks/rules';
import { mockOrders } from '../mocks/orders';
import { mockDelay } from '../mocks/utils';
import { apiGet, apiSend } from './client';
import { useMockData } from './dataSource';

export async function getRules(signal?: AbortSignal): Promise<RuleSummary[]> {
  if (!useMockData) return apiGet<RuleSummary[]>('/rules', signal);
  return mockDelay(mockRules, signal, 220);
}

export async function setRuleActive(id: string, active: boolean): Promise<RuleSummary> {
  if (!useMockData) return apiSend<RuleSummary>(`/rules/${id}`, 'PUT', { active });
  const rule = mockRules.find((item) => item.id === id);
  if (!rule) throw { code: 'RULE_NOT_FOUND', message: `Правило ${id} не найдено` };
  rule.active = active;
  rule.updatedAt = new Date().toISOString();
  return mockDelay(rule, undefined, 180);
}

export interface TestRuleResult {
  orderId: number;
  totalExecutors: number;
  eligibleExecutors: number;
  rejectedExecutors: number;
  explanation: string;
}

export async function testRules(orderId: number): Promise<TestRuleResult> {
  if (!useMockData) return apiSend<TestRuleResult>('/rules/test', 'POST', { orderId });
  const order = mockOrders.find((item) => item.id === orderId);
  if (!order) throw { code: 'ORDER_NOT_FOUND', message: `Заявка ${orderId} не найдена` };
  const eligibleExecutors = order.vip ? 2 : order.weight >= 5 ? 1 : 3;
  return mockDelay({ orderId, totalExecutors: 5, eligibleExecutors, rejectedExecutors: 5 - eligibleExecutors, explanation: order.vip ? 'VIP-фильтр оставил исполнителей с повышенным capacity weight.' : 'Применены активность, суточный лимит и профиль компетенций.' }, undefined, 260);
}
