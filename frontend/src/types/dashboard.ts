import type { Assignment } from './assignment';

export interface DashboardFilters {
  from?: string;
  to?: string;
  bucket: 'minute' | 'hour' | 'day';
}

export type MockScenario = 'normal' | 'high-throughput' | 'empty' | 'error';

export interface DashboardSummary {
  periodFrom: string;
  periodTo: string;
  generatedAt: string;
  totalOrders: number;
  assignedOrders: number;
  unassignedOrders: number;
  failedOrders: number;
  activeExecutors: number;
  pendingAssignments: number;
  ordersPerSecond: number;
  averageAssignmentTimeMs: number;
  p95AssignmentTimeMs: number;
  ruleRejections: number;
  reservationConflicts: number;
  errors: number;
}

export interface TimeSeriesPoint {
  timestamp: string;
  orders: number;
  assignments: number;
  failures: number;
}

export interface ExecutorLoadMetric {
  executorId: number;
  executorName: string;
  capacityWeight: number;
  confirmedWeight: number;
  pendingWeight: number;
  effectiveLoad: number;
  dailyCount: number;
  maxDailyLimit: number | null;
}

export interface FairnessMetric {
  kind: 'JAIN_INDEX' | 'DEVIATION_PERCENT';
  value: number;
  target: number | null;
  description: string;
}

export interface DashboardData {
  summary: DashboardSummary;
  timeline: TimeSeriesPoint[];
  executorLoads: ExecutorLoadMetric[];
  fairness: FairnessMetric;
  latestAssignments: Assignment[];
}
