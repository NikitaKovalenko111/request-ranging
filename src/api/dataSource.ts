import { env } from '../shared/config/env';

export const useMockData = env.dataSource === 'mock';
export const POLL_INTERVAL_MS = env.pollIntervalMs; //для совместимости
