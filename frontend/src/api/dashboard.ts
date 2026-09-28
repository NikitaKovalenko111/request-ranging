import type { DashboardData, DashboardFilters, MockScenario } from '../types/dashboard';
import { mockDashboard } from '../mocks/dashboard';
import { mockDelay } from '../mocks/utils';
import { apiGet } from './client';
import { useMockData } from './dataSource';

function toParams(filters: DashboardFilters): string {
  const params = new URLSearchParams({ bucket: filters.bucket });
  if (filters.from) params.set('from', filters.from);
  if (filters.to) params.set('to', filters.to);
  return params.toString();
}

export async function getDashboard(filters: DashboardFilters, scenario: MockScenario, signal?: AbortSignal): Promise<DashboardData> {
  if (useMockData) {
    if (scenario === 'error') throw { code: 'MOCK_DASHBOARD_ERROR', message: 'Демонстрационная ошибка Dashboard', traceId: 'mock-dashboard-500' };
    const multiplier = scenario === 'high-throughput' ? 8 : 1;
    const liveData: DashboardData = {
      ...mockDashboard,
      summary: {
        ...mockDashboard.summary,
        periodFrom: filters.from || mockDashboard.summary.periodFrom,
        periodTo: filters.to || new Date().toISOString(),
        generatedAt: new Date().toISOString(),
        ordersPerSecond: mockDashboard.summary.ordersPerSecond * multiplier,
        totalOrders: mockDashboard.summary.totalOrders * multiplier,
      },
      timeline: scenario === 'empty' ? [] : mockDashboard.timeline.map((point) => ({ ...point, orders: point.orders * multiplier, assignments: point.assignments * multiplier })),
      executorLoads: scenario === 'empty' ? [] : mockDashboard.executorLoads,
      latestAssignments: scenario === 'empty' ? [] : mockDashboard.latestAssignments,
    };
    return mockDelay(liveData, signal);
  }
  return apiGet<DashboardData>(`/dashboard?${toParams(filters)}`, signal);
}

export async function getMetrics(filters: DashboardFilters, signal?: AbortSignal): Promise<DashboardData> {
  if (useMockData) return getDashboard(filters, 'normal', signal);
  return apiGet<DashboardData>(`/metrics?${toParams(filters)}`, signal);
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
    ['Summary', 'Среднее время, с', data.summary.averageAssignmentTimeMs],
    ['Summary', 'p95, с', data.summary.p95AssignmentTimeMs],
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

export async function exportDashboardXlsx(data: DashboardData): Promise<void> {
  const { default: writeXlsxFile } = await import('write-excel-file/browser');
  const rows = (values: Array<Array<string | number | null>>) => values.map((row, rowIndex) => row.map((value) => ({ value: value ?? '', fontWeight: rowIndex === 0 ? 'bold' as const : undefined, backgroundColor: rowIndex === 0 ? '#E8F1F7' : undefined })));
  const summary = rows([
    ['Показатель', 'Значение'],
    ['Период с', data.summary.periodFrom], ['Период по', data.summary.periodTo], ['Сформировано', data.summary.generatedAt],
    ['Всего заявок', data.summary.totalOrders], ['Назначено', data.summary.assignedOrders], ['Не назначено', data.summary.unassignedOrders],
    ['Активные исполнители', data.summary.activeExecutors], ['Среднее время, с', data.summary.averageAssignmentTimeMs], ['p95, с', data.summary.p95AssignmentTimeMs],
    ['Fairness type', data.fairness.kind], ['Fairness value', data.fairness.value], ['Fairness target', data.fairness.target],
  ]);
  const assignments = rows([
    ['orderId', 'executorId', 'executorName', 'status', 'processingTimeMs', 'createdAt', 'confirmedAt'],
    ...data.latestAssignments.map((item) => [item.orderId, item.executorId, item.executorName, item.status, item.processingTimeMs, item.createdAt, item.confirmedAt]),
  ]);
  const executorLoad = rows([
    ['executorId', 'executorName', 'capacityWeight', 'confirmedWeight', 'pendingWeight', 'effectiveLoad', 'dailyCount', 'maxDailyLimit'],
    ...data.executorLoads.map((item) => [item.executorId, item.executorName, item.capacityWeight, item.confirmedWeight, item.pendingWeight, item.effectiveLoad, item.dailyCount, item.maxDailyLimit]),
  ]);
  const stamp = new Date().toISOString().slice(0, 16).replaceAll(':', '').replace('T', '-');
  await writeXlsxFile([
    { data: summary, sheet: 'Summary', columns: [{ width: 28 }, { width: 34 }], stickyRowsCount: 1 },
    { data: assignments, sheet: 'Assignments', columns: [{ width: 12 }, { width: 12 }, { width: 24 }, { width: 16 }, { width: 18 }, { width: 24 }, { width: 24 }], stickyRowsCount: 1 },
    { data: executorLoad, sheet: 'Executor Load', columns: [{ width: 12 }, { width: 24 }, { width: 16 }, { width: 17 }, { width: 15 }, { width: 16 }, { width: 13 }, { width: 17 }], stickyRowsCount: 1 },
  ]).toFile(`executor-balancer-report-${stamp}.xlsx`);
}
