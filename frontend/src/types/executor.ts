export type ExecutorStatus = 'ACTIVE' | 'INACTIVE';

export interface Executor {
  id: string;
  firstName: string;
  lastName: string;
  middleName: string | null;
  displayName: string;
  status: ExecutorStatus;
  qualification: string | null;
  capacityWeight: number;
  confirmedWeight: number;
  pendingWeight: number;
  effectiveLoad: number;
  dailyCount: number;
  maxDailyLimit: number | null;
  lastAssignmentAt: string | null;
  parameters?: Record<string, unknown>;
}

export interface ExecutorOption {
  id: string;
  displayName: string;
  status: ExecutorStatus;
}

export interface UpdateExecutorRequest {
  status?: ExecutorStatus;
}

export interface ExecutorFilters {
  status?: ExecutorStatus;
  search?: string;
  limit?: number;
  offset?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}
