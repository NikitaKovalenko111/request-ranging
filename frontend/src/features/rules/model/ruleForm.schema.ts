import { z } from 'zod';
import type { RuleSchema } from '../../../types/ruleSchema';

const operatorEnum = z.enum([
    'EQ', 'NE', 'GT', 'GTE', 'LT', 'LTE', 'IN', 'NOT_IN', 'BETWEEN', 'CONTAINS',
]);

const scalar = z.union([z.string(), z.number(), z.boolean(), z.null()]);

const fieldReferenceSchema = z.object({
    type: z.literal('FIELD'),
    source: z.enum(['ORDER', 'EXECUTOR']),
    field: z.string().min(1, 'Выберите поле'),
});

const constantSchema = z.object({
    type: z.literal('CONSTANT'),
    value: z.union([scalar, z.array(scalar)]),
});

const operandSchema = z.discriminatedUnion('type', [
    fieldReferenceSchema,
    constantSchema,
]);

const expressionSchema = z
    .object({
        left: fieldReferenceSchema,
        operator: operatorEnum,
        right: operandSchema,
    })
    .superRefine((expr, ctx) => {
        if (expr.right.type !== 'CONSTANT') return;
        const v = expr.right.value;
        if (expr.operator === 'BETWEEN') {
            if (!Array.isArray(v) || v.length !== 2) {
                ctx.addIssue({
                    code: z.ZodIssueCode.custom,
                    path: ['right', 'value'],
                    message: 'BETWEEN требует ровно 2 значения',
                });
            }
        }
        if (expr.operator === 'IN' || expr.operator === 'NOT_IN') {
            if (!Array.isArray(v) || v.length < 1) {
                ctx.addIssue({
                    code: z.ZodIssueCode.custom,
                    path: ['right', 'value'],
                    message: 'Нужно минимум одно значение',
                });
            }
        }
        if (typeof v === 'number' && Number.isNaN(v)) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ['right', 'value'],
                message: 'Не число',
            });
        }
    });

export const ruleFormSchema = z.object({
    name: z.string().trim().min(1, 'Название обязательно').max(200, 'Слишком длинное'),
    description: z.string().nullable(),
    when: z.array(expressionSchema),
    requirements: z.array(expressionSchema).min(1, 'Нужно минимум одно требование'),
    logic: z.literal('AND'),
    priority: z.number({ error: 'Введите число' }).int('Целое').min(0, 'Не меньше 0'),
    active: z.boolean(),
});

export type RuleFormValues = z.infer<typeof ruleFormSchema>;

// Опционально: проверка полей по Rule Schema
export function validateAgainstSchema(values: RuleFormValues, schema: RuleSchema) {
    const allFields = [...schema.orderFields, ...schema.executorFields];
    const errors: { path: (string | number)[]; message: string }[] = [];
    const checkExpr = (arr: RuleFormValues['when'], base: string) => {
        arr.forEach((expr, i) => {
            const def = allFields.find((f) => f.name === expr.left.field);
            if (!def) {
                errors.push({
                    path: [`${base}.${i}.left.field`],
                    message: `Поле "${expr.left.field}" не найдено в схеме`,
                });
                return;
            }
            if (!def.allowedOperators.includes(expr.operator)) {
                errors.push({
                    path: [`${base}.${i}.operator`],
                    message: `Оператор ${expr.operator} не разрешён для "${def.label}"`,
                });
            }
        });
    };
    checkExpr(values.when, 'when');
    checkExpr(values.requirements, 'requirements');
    return errors;
}