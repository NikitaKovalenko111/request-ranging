import type { Assignment } from '../types/assignment';
import type { DecisionTrace } from '../types/decisionTrace';
import { mockAssignments, mockDecisionTraces } from '../mocks/assignments';
import { mockDelay } from '../mocks/utils';
import { apiGet } from './client';
import { useMockData } from './dataSource';

export async function getAssignment(orderId: number, signal?: AbortSignal): Promise<Assignment | null> {
  if (!useMockData) return apiGet<Assignment | null>(`/assignments/${orderId}`, signal);
  return mockDelay(mockAssignments.find((item) => item.orderId === orderId) ?? null, signal, 230);
}

export async function getDecisionTrace(orderId: number, signal?: AbortSignal): Promise<DecisionTrace | null> {
  if (!useMockData) return apiGet<DecisionTrace | null>(`/assignments/${orderId}/decision-trace`, signal);
  return mockDelay(mockDecisionTraces[orderId] ?? null, signal, 320);
}

