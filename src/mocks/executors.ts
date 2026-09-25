import type { ExecutorSummary } from '../types/executor';

export const mockExecutors: ExecutorSummary[] = [
  { id: 28, displayName: 'Петров И. В.', status: 'ACTIVE', qualification: 'Международное право', capacityWeight: 1.5, confirmedWeight: 4, pendingWeight: 1, effectiveLoad: 3.33, dailyCount: 17, maxDailyLimit: 40 },
  { id: 11, displayName: 'Соколова М. А.', status: 'ACTIVE', qualification: 'Финансы', capacityWeight: 1.7, confirmedWeight: 6, pendingWeight: 2, effectiveLoad: 4.71, dailyCount: 22, maxDailyLimit: 45 },
  { id: 7, displayName: 'Ахметов Р. С.', status: 'ACTIVE', qualification: 'Комплаенс', capacityWeight: 2, confirmedWeight: 4, pendingWeight: 1, effectiveLoad: 2.5, dailyCount: 19, maxDailyLimit: 40 },
  { id: 19, displayName: 'Ким А. Л.', status: 'ACTIVE', qualification: 'Налоговое право', capacityWeight: 1, confirmedWeight: 2, pendingWeight: 0, effectiveLoad: 2, dailyCount: 12, maxDailyLimit: 30 },
  { id: 34, displayName: 'Орлова Е. Н.', status: 'INACTIVE', qualification: 'Санкционный контроль', capacityWeight: 1.5, confirmedWeight: 9, pendingWeight: 0, effectiveLoad: 6, dailyCount: 40, maxDailyLimit: 40 },
];

