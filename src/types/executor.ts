export type ExecutorStatus = 'ACTIVE' | 'INACTIVE';

export interface ExecutorSummary {
  id: number;
  displayName: string;
  status: ExecutorStatus;
  qualification: string | null;
  capacityWeight: number;
  confirmedWeight: number;
  pendingWeight: number;
  effectiveLoad: number;
  dailyCount: number;
  maxDailyLimit: number | null;
}

