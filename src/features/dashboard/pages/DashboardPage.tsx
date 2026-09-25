import { Activity, CircleGauge, Clock3, Download, Gauge, Inbox, UserCheck, Zap } from 'lucide-react';
import type { ApiError } from '../../../types/api';
import { exportDashboardCsv } from '../../../api/dashboard';
import { DataFreshness } from '../../../shared/components/DataFreshness';
import { EmptyState, ErrorState, LoadingState } from '../../../shared/components/StateViews';
import { formatDuration, formatNumber } from '../../../shared/format';
import { ExecutorLoadChart } from '../components/ExecutorLoadChart';
import { FairnessCard } from '../components/FairnessCard';
import { KpiCard } from '../components/KpiCard';
import { LatestAssignmentsTable } from '../components/LatestAssignmentsTable';
import { OrdersTimelineChart } from '../components/OrdersTimelineChart';
import { useDashboard } from '../hooks/useDashboard';

export function DashboardPage() {
  const query = useDashboard();
  if (query.isLoading) return <LoadingState rows={6} />;
  if (query.isError) { const error = query.error as unknown as ApiError; return <ErrorState message={error.message ?? 'Неизвестная ошибка'} traceId={error.traceId} onRetry={() => void query.refetch()} />; }
  if (!query.data || query.data.timeline.length === 0) return <EmptyState title="За выбранный период данных нет" />;
  const { summary } = query.data;
  return <div className="page-stack">
    <div className="page-actions"><div><h2 className="page-lead">Распределение в реальном времени</h2><p>Поток заявок, скорость решений и баланс нагрузки.</p></div><div className="action-row"><DataFreshness updatedAt={query.dataUpdatedAt} fetching={query.isFetching} /><button className="button secondary" onClick={() => exportDashboardCsv(query.data)}><Download size={16} />Экспорт CSV</button></div></div>
    <section className="kpi-grid">
      <KpiCard label="Всего заявок" value={formatNumber(summary.totalOrders)} icon={Inbox} tone="teal" />
      <KpiCard label="Назначено" value={formatNumber(summary.assignedOrders)} icon={UserCheck} tone="blue" />
      <KpiCard label="Не назначено" value={formatNumber(summary.unassignedOrders)} icon={Activity} tone="rose" />
      <KpiCard label="Активные исполнители" value={formatNumber(summary.activeExecutors)} icon={Gauge} tone="violet" />
      <KpiCard label="Среднее время" value={formatDuration(summary.averageAssignmentTimeMs)} icon={Clock3} tone="amber" hint="Среднее время от получения заявки до результата назначения." />
      <KpiCard label="p95 времени" value={formatDuration(summary.p95AssignmentTimeMs)} icon={CircleGauge} tone="cyan" hint="95% решений принимаются не дольше указанного времени." />
      <KpiCard label="Throughput" value={formatNumber(summary.ordersPerSecond)} unit="заявок/с" icon={Zap} tone="teal" />
      <KpiCard label="Ожидают подтверждения" value={formatNumber(summary.pendingAssignments)} icon={Activity} tone="amber" />
    </section>
    <div className="dashboard-grid"><OrdersTimelineChart data={query.data.timeline} /><ExecutorLoadChart data={query.data.executorLoads} /></div>
    <div className="dashboard-bottom"><FairnessCard data={query.data} /><LatestAssignmentsTable items={query.data.latestAssignments} /></div>
  </div>;
}
