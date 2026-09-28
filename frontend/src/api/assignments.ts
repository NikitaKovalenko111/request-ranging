import type { AssignmentDetails } from '../types/assignment';
import { mockAssignments, mockDecisionTraces } from '../mocks/assignments';
import { mockDelay } from '../mocks/utils';
import { apiGet } from './client';
import { useMockData } from './dataSource';

export async function getAssignmentByOrderId(orderId: string, signal?: AbortSignal): Promise<AssignmentDetails> {
  if (!useMockData) return apiGet<AssignmentDetails>(`/assignments/${encodeURIComponent(orderId)}`, signal);
  return mockDelay({
    assignment: mockAssignments.find((item) => item.orderId === orderId) ?? null,
    decisionTrace: mockDecisionTraces[orderId] ?? null,
  }, signal, 300);
}
