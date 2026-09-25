import type { ApiError } from '../types/api';
import { env } from '../shared/config/env';

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, { signal, headers: { Accept: 'application/json' } });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw { code: 'NETWORK_ERROR', message: 'Backend недоступен. Проверьте соединение и повторите запрос.' } satisfies ApiError;
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: ApiError } | null;
    throw {
      code: body?.error?.code ?? `HTTP_${response.status}`,
      message: body?.error?.message ?? 'Не удалось получить данные',
      traceId: body?.error?.traceId,
      status: response.status,
    } satisfies ApiError;
  }

  return response.json() as Promise<T>;
}

export async function apiSend<T>(path: string, method: 'POST' | 'PATCH' | 'PUT' | 'DELETE', body?: unknown, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      method,
      signal,
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: body == null ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw { code: 'NETWORK_ERROR', message: 'Backend недоступен. Проверьте соединение и повторите запрос.' } satisfies ApiError;
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { error?: ApiError } | null;
    throw { code: payload?.error?.code ?? `HTTP_${response.status}`, message: payload?.error?.message ?? 'Операция не выполнена', traceId: payload?.error?.traceId, status: response.status } satisfies ApiError;
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
