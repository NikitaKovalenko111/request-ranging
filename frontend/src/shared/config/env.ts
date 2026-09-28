const rawSource = import.meta.env.VITE_DATA_SOURCE
  ?? (import.meta.env.MODE === 'test' ? 'mock' : 'api');

const rawPoll = import.meta.env.VITE_POLL_INTERVAL_MS;
const parsedPoll = rawPoll === undefined || rawPoll === ''
  ? 2000
  : Number(rawPoll);
const pollIntervalMs =
  Number.isFinite(parsedPoll) && parsedPoll > 0 ? parsedPoll : 2000;

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  dataSource: rawSource === 'api' ? 'api' : 'mock',
  pollIntervalMs,
  realtimeMode: import.meta.env.VITE_REALTIME_MODE === 'sse' ? 'sse' : 'polling',
} as const;
