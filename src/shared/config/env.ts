const rawSource = import.meta.env.VITE_DATA_SOURCE ?? 'mock';

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api/v1',
  dataSource: rawSource === 'api' ? 'api' : 'mock',
  pollIntervalMs: Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 2000),
  realtimeMode: import.meta.env.VITE_REALTIME_MODE === 'sse' ? 'sse' : 'polling',
} as const;
