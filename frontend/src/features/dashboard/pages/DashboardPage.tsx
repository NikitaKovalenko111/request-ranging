import { useState } from 'react';
import { Activity, CircleGauge, Clock3, Download, FileSpreadsheet, Gauge, Inbox, UserCheck, Zap } from 'lucide-react';
import type { ApiError } from '../../../types/api';
import type { DashboardData, DashboardFilters, MockScenario } from '../../../types/dashboard';
import { exportDashboardCsv, exportDashboardXlsx } from '../../../api/dashboard';
import { useMockData } from '../../../api/dataSource';
import { DataFreshness } from '../../../shared/components/DataFreshness';
import { EmptyState, ErrorState, LoadingState } from '../../../shared/components/StateViews';
import { formatDuration, formatNumber } from '../../../shared/format';
import { useDashboardRealtime } from '../../../shared/hooks/useDashboardRealtime';
import { ExecutorLoadChart } from '../components/ExecutorLoadChart';
import { KpiCard } from '../components/KpiCard';
import { LatestAssignmentsTable } from '../components/LatestAssignmentsTable';
import { OrdersTimelineChart } from '../components/OrdersTimelineChart';
import { useDashboard } from '../hooks/useDashboard';

const toLocalInput = (date: Date) => {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
};

const initialFilters: DashboardFilters = {
  bucket: 'minute',
};

export function DashboardPage() {
  useDashboardRealtime();
  const [filters, setFilters] = useState<DashboardFilters>(initialFilters);
  const [scenario, setScenario] = useState<MockScenario>('normal');
  const [exporting, setExporting] = useState(false);
  const query = useDashboard(filters, scenario);

  const setDate = (key: 'from' | 'to', value: string) => setFilters((current) => ({ ...current, [key]: value ? new Date(value).toISOString() : undefined }));
  const exportXlsx = async () => {
    if (!query.data) return;
    setExporting(true);
    try { await exportDashboardXlsx(query.data); } finally { setExporting(false); }
  };

  return <div className="page-stack">
    <div className="page-actions"><div><h2 className="page-lead">Распределение в реальном времени</h2><p>Поток заявок, скорость решений и баланс нагрузки.</p></div><div className="action-row"><DataFreshness updatedAt={query.dataUpdatedAt || undefined} fetching={query.isFetching} />{query.data && <><button className="button secondary" onClick={() => exportDashboardCsv(query.data)}><Download size={16} />CSV</button><button className="button secondary" disabled={exporting} onClick={() => void exportXlsx()}><FileSpreadsheet size={16} />{exporting ? 'Формируем…' : 'XLSX'}</button></>}</div></div>
    <section className="dashboard-controls panel">
      <label><span>С (час назад)</span><input type="datetime-local" value={filters.from ? toLocalInput(new Date(filters.from)) : ''} onChange={(event) => setDate('from', event.target.value)} /></label>
      <label><span>По (сейчас)</span><input type="datetime-local" value={filters.to ? toLocalInput(new Date(filters.to)) : ''} onChange={(event) => setDate('to', event.target.value)} /></label>
      <label><span>Группировка</span><select value={filters.bucket} onChange={(event) => setFilters((current) => ({ ...current, bucket: event.target.value as DashboardFilters['bucket'] }))}><option value="minute">По минутам</option><option value="hour">По часам</option><option value="day">По дням</option></select></label>
      {useMockData && <label><span>Mock-сценарий</span><select value={scenario} onChange={(event) => setScenario(event.target.value as MockScenario)}><option value="normal">Нормальная нагрузка</option><option value="high-throughput">Высокий throughput</option><option value="empty">Пустой период</option><option value="error">Ошибка API</option></select></label>}
    </section>
    {query.isLoading ? <LoadingState rows={6} /> : query.isError ? <ErrorState message={(query.error as unknown as ApiError).message ?? 'Неизвестная ошибка'} traceId={(query.error as unknown as ApiError).traceId} onRetry={() => void query.refetch()} /> : !query.data || query.data.timeline.length === 0 ? <EmptyState title="За выбранный период данных нет" /> : <DashboardContent data={query.data} />}
  </div>;
}

function DashboardContent({ data }: { data: DashboardData }) {
  const { summary } = data;
  return <>
    <section className="kpi-grid">
      <KpiCard label="Всего заявок" value={formatNumber(summary.totalOrders)} icon={Inbox} tone="teal" />
      <KpiCard label="Назначено" value={formatNumber(summary.assignedOrders)} icon={UserCheck} tone="blue" />
      <KpiCard label="Не назначено" value={formatNumber(summary.unassignedOrders)} icon={Activity} tone="rose" />
      <KpiCard label="Активные исполнители" value={formatNumber(summary.activeExecutors)} icon={Gauge} tone="violet" />
      <KpiCard label="Среднее время" value={formatDuration(summary.averageAssignmentTimeMs)} icon={Clock3} tone="amber" hint="Средняя длительность обработки решения. Backend измеряет её в миллисекундах." />
      <KpiCard label="p95 времени" value={formatDuration(summary.p95AssignmentTimeMs)} icon={CircleGauge} tone="cyan" hint="95% решений принимаются не дольше указанного времени. Backend измеряет его в миллисекундах." />
      <KpiCard label="Throughput" value={formatNumber(summary.ordersPerSecond)} unit="заявок/с" icon={Zap} tone="teal" />
      <KpiCard label="Ожидают подтверждения" value={formatNumber(summary.pendingAssignments)} icon={Activity} tone="amber" />
    </section>
    <div className="dashboard-grid"><OrdersTimelineChart data={data.timeline} /><ExecutorLoadChart data={data.executorLoads} /></div>
    <div className="dashboard-bottom"><LatestAssignmentsTable items={data.latestAssignments} /></div>
  </>;
}
