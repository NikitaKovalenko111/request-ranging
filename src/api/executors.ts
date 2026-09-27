import { apiClient } from './client';
import { useMockData } from './dataSource';
import { mockExecutors } from '../mocks/executors';
import type { Executor, ExecutorFilters, UpdateExecutorRequest } from '../types/executor';
import type { PaginatedResponse, RequestOptions } from '../types/api';

let inMemory: Executor[] = [...mockExecutors];
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

function applyFilters(items: Executor[], filters: ExecutorFilters): Executor[] {
  let result = items;
  if (filters.status) result = result.filter((e) => e.status === filters.status);
  if (filters.search) {
    const q = filters.search.toLowerCase();
    result = result.filter((e) => e.displayName.toLowerCase().includes(q));
  }
  return result;
}

export async function getExecutors(
  filters: ExecutorFilters,
  signal?: AbortSignal,
): Promise<PaginatedResponse<Executor>> {
  if (useMockData) {
    await delay(300);
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    const filtered = applyFilters(inMemory, filters);
    const offset = filters.offset ?? 0;
    const limit = filters.limit ?? 20;
    return {
      items: filtered.slice(offset, offset + limit),
      pagination: { limit, offset, total: filtered.length },
    };
  }
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') params.append(k, String(v));
  });
  return apiClient.get(`/executors?${params.toString()}`, { signal });
}

export async function getExecutor(id: number, options?: RequestOptions): Promise<Executor> {
  if (useMockData) {
    await delay(200);
    const found = inMemory.find((e) => e.id === id);
    if (!found) throw new Error('Executor not found');
    return found;
  }
  return apiClient.get(`/executors/${id}`, options);
}

export async function updateExecutor(id: number, patch: UpdateExecutorRequest): Promise<Executor> {
  if (useMockData) {
    await delay(300);
    const idx = inMemory.findIndex((e) => e.id === id);
    if (idx === -1) throw new Error('Executor not found');
    inMemory[idx] = { ...inMemory[idx], ...patch };
    return inMemory[idx];
  }
  return apiClient.patch(`/executors/${id}`, patch);
}
