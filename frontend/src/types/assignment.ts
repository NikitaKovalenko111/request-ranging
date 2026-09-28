import type { AssignmentStatus } from './order';
import type { DecisionTrace } from './decisionTrace';

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

export interface AssignmentDetails {
  assignment: Assignment | null;
  decisionTrace: DecisionTrace | null;
}
