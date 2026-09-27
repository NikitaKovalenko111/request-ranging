export type RuleOperator =
    | 'EQ'
    | 'NE'
    | 'GT'
    | 'GTE'
    | 'LT'
    | 'LTE'
    | 'IN'
    | 'NOT_IN'
    | 'BETWEEN'
    | 'CONTAINS';

export type FieldDataType =
    | 'STRING'
    | 'NUMBER'
    | 'BOOLEAN'
    | 'ENUM'
    | 'UUID'
    | 'STRING_ARRAY';

export interface RuleFieldOption {
    value: string | number | boolean;
    label: string;
}

export interface RuleFieldDefinition {
    source: 'ORDER' | 'EXECUTOR';
    name: string;
    label: string;
    dataType: FieldDataType;
    nullable: boolean;
    allowedOperators: RuleOperator[];
    options?: RuleFieldOption[];
    description?: string;
}

export interface RuleSchema {
    version: string;
    orderFields: RuleFieldDefinition[];
    executorFields: RuleFieldDefinition[];
}

export const OPERATOR_LABELS: Record<RuleOperator, string> = {
    EQ: '=',
    NE: '!=',
    GT: '>',
    GTE: '>=',
    LT: '<',
    LTE: '<=',
    IN: 'IN',
    NOT_IN: 'NOT IN',
    BETWEEN: 'BETWEEN',
    CONTAINS: 'CONTAINS',
};