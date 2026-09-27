import type { Rule, RuleExpression } from '../../../types/rule';
import { OPERATOR_LABELS, type RuleFieldDefinition } from '../../../types/ruleSchema';

function fieldLabel(field: string, allFields: RuleFieldDefinition[]): string {
    const def = allFields.find((f) => f.name === field);
    return def?.label ?? field;
}

function formatRight(expr: RuleExpression, allFields: RuleFieldDefinition[]): string {
    const right = expr.right;
    if (right.type === 'FIELD') {
        return fieldLabel(right.field, allFields);
    }
    const value = right.value;
    if (Array.isArray(value)) return `[${value.map(String).join(', ')}]`;
    if (typeof value === 'boolean') return value ? 'Да' : 'Нет';
    return String(value ?? '—');
}

export function RuleHumanReadable({
    rule,
    orderFields,
    executorFields,
}: {
    rule: Rule;
    orderFields: RuleFieldDefinition[];
    executorFields: RuleFieldDefinition[];
}) {
    const all = [...orderFields, ...executorFields];
    const render = (exprs: RuleExpression[]) =>
        exprs
            .map((e) => {
                const left = fieldLabel(e.left.field, all);
                return `${left} ${OPERATOR_LABELS[e.operator]} ${formatRight(e, all)}`;
            })
            .join(' И ');

    const when = rule.when.length ? `Если ${render(rule.when)}, ` : '';
    const req = render(rule.requirements);
    return <span>{`${when}требуется ${req}`}</span>;
}