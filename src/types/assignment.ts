import type { AssignmentStatus } from './order';

export interface Assignment {
  orderId: number;
  executorId: number | null;
  executorName: string | null;
  status: AssignmentStatus;
  createdAt: string;
  reservedAt: string | null;
  confirmedAt: string | null;
  processingTimeMs: number | null;
  explanation: string | null;
}

