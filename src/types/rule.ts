import type { RuleOperator } from './ruleSchema';

export type RuleScalar = string | number | boolean | null;

export interface RuleFieldReference {
  type: 'FIELD';
  source: 'ORDER' | 'EXECUTOR';
  field: string;
}

export interface RuleConstant {
  type: 'CONSTANT';
  value: RuleScalar | RuleScalar[];
}

export type RuleOperand = RuleFieldReference | RuleConstant;

export interface RuleExpression {
  left: RuleFieldReference;
  operator: RuleOperator;
  right: RuleOperand;
}

export interface Rule {
  id: string;
  name: string;
  description: string | null;
  when: RuleExpression[];
  requirements: RuleExpression[];
  logic: 'AND';
  priority: number;
  active: boolean;
  createdAt: string;
  updatedAt: string;
  version?: number;
}

export type RuleDraft = Omit<Rule, 'id' | 'createdAt' | 'updatedAt' | 'version'>;

export interface RuleFilters {
  active?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface TestRuleRequest {
  rule: RuleDraft;
  orderId: number;
  executorId: number;
}

export interface RuleTestComparison {
  leftField: string;
  leftValue: unknown;
  operator: RuleOperator;
  rightSource: 'CONSTANT' | 'ORDER_FIELD' | 'EXECUTOR_FIELD';
  rightValue: unknown;
}

export interface TestRuleResponse {
  result: 'PASS' | 'FAIL';
  reason: string;
  comparisons: RuleTestComparison[];
}
