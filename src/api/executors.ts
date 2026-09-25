import type { ExecutorSummary } from '../types/executor';
import { mockExecutors } from '../mocks/executors';
import { mockDelay } from '../mocks/utils';
import { apiGet, apiSend } from './client';
import { useMockData } from './dataSource';

export async function getExecutors(signal?: AbortSignal): Promise<ExecutorSummary[]> {
  if (!useMockData) return apiGet<ExecutorSummary[]>('/executors', signal);
  return mockDelay(mockExecutors, signal, 220);
}

export async function setExecutorStatus(id: number, status: ExecutorSummary['status']): Promise<ExecutorSummary> {
  if (!useMockData) return apiSend<ExecutorSummary>(`/executors/${id}`, 'PATCH', { status });
  const executor = mockExecutors.find((item) => item.id === id);
  if (!executor) throw { code: 'EXECUTOR_NOT_FOUND', message: `Исполнитель ${id} не найден` };
  executor.status = status;
  return mockDelay(executor, undefined, 180);
}
