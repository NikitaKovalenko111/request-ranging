export type OrderStatus = 'processed' | 'await' | 'accept' | 'reject';
export type AssignmentStatus = 'pending' | 'reserved' | 'assigned' | 'unassigned' | 'failed';

export interface Order {
  id: number;
  parentId: number | null;
  assignedExecutorId: number | null;
  assignedExecutorName: string | null;
  sum: number | null;
  clientMsp: string | null;
  executorMsp: string | null;
  orderType: string;
  subject: string;
  vip: boolean;
  weight: number;
  text: string;
  status: OrderStatus;
  assignmentStatus: AssignmentStatus;
  createdAt: string;
  assignedAt: string | null;
  processingTimeMs: number | null;
  explanation: string | null;
}

export interface OrderFilters {
  id: string;
  status: OrderStatus | '';
  assignmentStatus: AssignmentStatus | '';
  orderType: string;
  vip: '' | 'true' | 'false';
  parentOnly: boolean;
}

