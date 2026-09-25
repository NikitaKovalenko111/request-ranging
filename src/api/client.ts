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

