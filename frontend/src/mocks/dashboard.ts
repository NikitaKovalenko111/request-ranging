import type { DashboardData } from '../types/dashboard';
import { mockAssignments } from './assignments';

const now = Date.now();
const point = (minutes: number, orders: number, assignments: number, failures: number) => ({ timestamp: new Date(now - minutes * 60_000).toISOString(), orders, assignments, failures });

export const mockDashboard: DashboardData = {
  summary: {
    periodFrom: new Date(now - 60 * 60_000).toISOString(),
    periodTo: new Date(now).toISOString(),
    generatedAt: new Date(now).toISOString(),
    totalOrders: 1248,
    assignedOrders: 1219,
    unassignedOrders: 17,
    failedOrders: 12,
    activeExecutors: 41,
    pendingAssignments: 18,
    ordersPerSecond: 12.4,
    averageAssignmentTimeMs: 48,
    p95AssignmentTimeMs: 95,
    ruleRejections: 340,
    reservationConflicts: 14,
    errors: 3,
  },
  timeline: [point(50, 72, 69, 1), point(40, 94, 90, 2), point(30, 128, 123, 1), point(20, 116, 114, 1), point(10, 151, 147, 3), point(0, 164, 159, 2)],
  executorLoads: [
    { executorId: '28', executorName: 'Петров И. В.', capacityWeight: 1.5, confirmedWeight: 4, pendingWeight: 1, effectiveLoad: 3.33, dailyCount: 17, maxDailyLimit: 40 },
    { executorId: '29', executorName: 'Соколова М. А.', capacityWeight: 1.7, confirmedWeight: 6, pendingWeight: 2, effectiveLoad: 4.71, dailyCount: 22, maxDailyLimit: 45 },
    { executorId: '30', executorName: 'Ахметов Р. С.', capacityWeight: 2, confirmedWeight: 4, pendingWeight: 1, effectiveLoad: 2.5, dailyCount: 19, maxDailyLimit: 40 },
    { executorId: '31', executorName: 'Ким А. Л.', capacityWeight: 1, confirmedWeight: 2, pendingWeight: 0, effectiveLoad: 2, dailyCount: 12, maxDailyLimit: 30 },
    { executorId: '32', executorName: 'Орлова Е. Н.', capacityWeight: 1.5, confirmedWeight: 9, pendingWeight: 0, effectiveLoad: 6, dailyCount: 40, maxDailyLimit: 40 },
  ],
  fairness: { kind: 'JAIN_INDEX', value: 0.985, target: 0.98, description: '1.0 соответствует полностью равномерному распределению с учётом весов исполнителей.' },
  latestAssignments: mockAssignments.slice(0, 6),
};

