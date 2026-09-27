import type { ApiError } from '../types/api';
import { env } from '../shared/config/env';

// ─────────────────────────────────────────────────────────────
// Новый ApiClient по ТЗ §9.1
// ────────────────────────────────────────────────────────────

export interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

export interface ApiClient {
  get<T>(path: string, options?: RequestOptions): Promise<T>;
  post<TResponse, TBody>(path: string, body: TBody, options?: RequestOptions): Promise<TResponse>;
  put<TResponse, TBody>(path: string, body: TBody, options?: RequestOptions): Promise<TResponse>;
  patch<TResponse, TBody>(path: string, body: TBody, options?: RequestOptions): Promise<TResponse>;
  delete<T>(path: string, options?: RequestOptions): Promise<T>;
}

const DEFAULT_TIMEOUT_MS = 15_000;

async function request<T>(
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<T> {
  const controller = new AbortController();
  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  if (options?.signal) {
    if (options.signal.aborted) controller.abort();
    else options.signal.addEventListener('abort', () => controller.abort(), { once: true });
  }

  let response: Response;
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      method,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw {
      code: 'NETWORK_ERROR',
      message: 'Backend недоступен. Проверьте соединение и повторите запрос.',
    } satisfies ApiError;
  } finally {
    window.clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: ApiError } | null;
    throw {
      code: payload?.error?.code ?? `HTTP_${response.status}`,
      message: payload?.error?.message ?? 'Операция не выполнена',
      traceId: payload?.error?.traceId,
      fieldErrors: payload?.error?.fieldErrors,
      details: payload?.error?.details,
      status: response.status,
    } satisfies ApiError;
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const apiClient: ApiClient = {
  get: (path, options) => request('GET', path, undefined, options),
  post: (path, body, options) => request('POST', path, body, options),
  put: (path, body, options) => request('PUT', path, body, options),
  patch: (path, body, options) => request('PATCH', path, body, options),
  delete: (path, options) => request('DELETE', path, undefined, options),
};

// ─────────────────────────────────────────────────────────────
// Backward compatibility — старые функции первого разработчика.
// Сигнатуры и поведение сохранены один в один.
// ─────────────────────────────────────────────────────────────

/** @deprecated Используй apiClient.get */
export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>('GET', path, undefined, { signal });
}

/** @deprecated Используй apiClient.post / put / patch / delete */
export async function apiSend<T>(
  path: string,
  method: 'POST' | 'PATCH' | 'PUT' | 'DELETE',
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  return request<T>(method, path, body, { signal });
}