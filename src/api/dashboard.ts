import type { DashboardData } from '../types/dashboard';
import { mockDashboard } from '../mocks/dashboard';
import { mockDelay } from '../mocks/utils';
import { apiGet } from './client';
import { useMockData } from './dataSource';

export async function getDashboard(signal?: AbortSignal): Promise<DashboardData> {
  if (useMockData) {
    const liveData = { ...mockDashboard, summary: { ...mockDashboard.summary, generatedAt: new Date().toISOString() } };
    return mockDelay(liveData, signal);
  }
  return apiGet<DashboardData>('/dashboard?bucket=minute', signal);
}

const quoteCsv = (value: unknown) => `"${String(value ?? '').replaceAll('"', '""')}"`;

export function exportDashboardCsv(data: DashboardData): void {
  const rows = [
    ['Раздел', 'Показатель', 'Значение'],
    ['Summary', 'Период с', data.summary.periodFrom],
    ['Summary', 'Период по', data.summary.periodTo],
    ['Summary', 'Всего заявок', data.summary.totalOrders],
    ['Summary', 'Назначено', data.summary.assignedOrders],
    ['Summary', 'Не назначено', data.summary.unassignedOrders],
    ['Summary', 'Активные исполнители', data.summary.activeExecutors],
    ['Summary', 'Среднее время, мс', data.summary.averageAssignmentTimeMs],
    ['Summary', 'p95, мс', data.summary.p95AssignmentTimeMs],
    ['Summary', `Fairness ${data.fairness.kind}`, data.fairness.value],
    [],
    ['Assignments', 'orderId', 'executorId', 'executorName', 'status', 'processingTimeMs', 'createdAt', 'confirmedAt'],
    ...data.latestAssignments.map((item) => ['', item.orderId, item.executorId, item.executorName, item.status, item.processingTimeMs, item.createdAt, item.confirmedAt]),
    [],
    ['Executor Load', 'executorId', 'executorName', 'capacityWeight', 'confirmedWeight', 'pendingWeight', 'effectiveLoad', 'dailyCount', 'maxDailyLimit'],
    ...data.executorLoads.map((item) => ['', item.executorId, item.executorName, item.capacityWeight, item.confirmedWeight, item.pendingWeight, item.effectiveLoad, item.dailyCount, item.maxDailyLimit]),
  ];
  const content = `\uFEFF${rows.map((row) => row.map(quoteCsv).join(';')).join('\n')}`;
  const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8' }));
  const anchor = document.createElement('a');
  const stamp = new Date().toISOString().slice(0, 16).replaceAll(':', '').replace('T', '-');
  anchor.href = url;
  anchor.download = `executor-balancer-report-${stamp}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

