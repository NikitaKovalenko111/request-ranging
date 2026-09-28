export type ReservationResult = 'SUCCESS' | 'CONFLICT' | 'SKIPPED';

export interface FailedRule {
  ruleId: string | null;
  ruleName: string | null;
  reason: string;
}

export interface CandidateDecision {
  executorId: string;
  executorName: string;
  active: boolean;
  passedRules: boolean;
  failedRules: FailedRule[];
  dailyLimitReached: boolean;
  rankScore: number | null;
  confirmedWeight: number;
  pendingWeight: number;
  effectiveLoad: number;
  reservationResult: ReservationResult;
  selected: boolean;
}

export interface ParentReuseDecision {
  attempted: boolean;
  parentOrderId: string | null;
  previousExecutorId: string | null;
  previousExecutorName: string | null;
  previousExecutorActive: boolean | null;
  parametersMatched: boolean | null;
  dailyLimitIgnored: boolean;
  reused: boolean;
  reason: string | null;
}

export interface DecisionStage {
  code: 'TOTAL' | 'ACTIVE' | 'RULE_ENGINE' | 'RANKING' | 'BALANCING' | 'RESERVATION' | 'ASSIGNMENT';
  label: string;
  inputCount: number;
  outputCount: number;
  durationMs: number | null;
}

export interface DecisionTrace {
  orderId: string;
  timestamp: string;
  processingTimeMs: number;
  modelVersion: string | null;
  rulesVersion: string | null;
  totalExecutors: number;
  activeExecutors: number;
  eligibleExecutors: number;
  topKExecutors: number | null;
  selectedExecutorId: string | null;
  explanation: string;
  stages: DecisionStage[];
  parentReuse: ParentReuseDecision;
  candidates: CandidateDecision[];
}

