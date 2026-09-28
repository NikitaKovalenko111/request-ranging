import { z } from 'zod';
import type { RuleDraft, RuleExpression, RuleScalar } from '../../../types/rule';
import type { RuleFieldDefinition, RuleSchema } from '../../../types/ruleSchema';

const scalarSchema = z.union([z.string(), z.number(), z.boolean(), z.null()]);
const fieldReferenceSchema = z.object({
  type: z.literal('FIELD'),
  source: z.enum(['ORDER', 'EXECUTOR']),
  field: z.string().min(1, 'Выберите поле'),
});
const operandSchema = z.discriminatedUnion('type', [
  fieldReferenceSchema,
  z.object({ type: z.literal('CONSTANT'), value: z.union([scalarSchema, z.array(scalarSchema)]) }),
]);
const expressionSchema = z.object({
  left: fieldReferenceSchema,
  operator: z.enum(['EQ', 'NE', 'GT', 'GTE', 'LT', 'LTE', 'IN', 'NOT_IN', 'BETWEEN', 'CONTAINS']),
  right: operandSchema,
});

const draftSchema = z.object({
  name: z.string().trim().min(1, 'Введите название правила'),
  description: z.string().nullable(),
  when: z.array(expressionSchema),
  requirements: z.array(expressionSchema).min(1, 'Добавьте хотя бы одно требование'),
  logic: z.literal('AND'),
  priority: z.number().int('Приоритет должен быть целым').min(0, 'Приоритет не может быть отрицательным'),
  active: z.boolean(),
});

function findField(schema: RuleSchema, source: 'ORDER' | 'EXECUTOR', name: string) {
  return (source === 'ORDER' ? schema.orderFields : schema.executorFields).find((field) => field.name === name);
}

function isBlank(value: RuleScalar | RuleScalar[]) {
  return value == null || value === '' || (Array.isArray(value) && value.length === 0);
}

function validateConstant(field: RuleFieldDefinition, expression: RuleExpression): string | null {
  if (expression.right.type !== 'CONSTANT') return null;
  const value = expression.right.value;
  if (isBlank(value)) return 'Укажите значение';
  if (expression.operator === 'BETWEEN') {
    if (!Array.isArray(value) || value.length !== 2 || value.some((item) => typeof item !== 'number' || !Number.isFinite(item))) return 'BETWEEN требует две числовые границы';
    if ((value[0] as number) > (value[1] as number)) return 'Нижняя граница не может быть больше верхней';
    return null;
  }
  if (expression.operator === 'IN' || expression.operator === 'NOT_IN') {
    return Array.isArray(value) && value.length > 0 ? null : 'Добавьте хотя бы одно значение';
  }
  if (Array.isArray(value)) return 'Оператор ожидает одно значение';
  if (field.dataType === 'NUMBER' && (typeof value !== 'number' || !Number.isFinite(value))) return 'Введите корректное число';
  if (field.dataType === 'BOOLEAN' && typeof value !== 'boolean') return 'Выберите Да или Нет';
  if (field.dataType === 'UUID' && typeof value === 'string' && !z.uuid().safeParse(value).success) return 'Введите корректный UUID';
  if (field.dataType === 'ENUM' && field.options && !field.options.some((option) => option.value === value)) return 'Выберите значение из списка';
  return null;
}

export function buildRuleDraftSchema(schema: RuleSchema) {
  return draftSchema.superRefine((draft, context) => {
    const groups: Array<['when' | 'requirements', RuleExpression[]]> = [
      ['when', draft.when],
      ['requirements', draft.requirements],
    ];
    for (const [group, expressions] of groups) {
      expressions.forEach((expression, index) => {
        const left = findField(schema, expression.left.source, expression.left.field);
        if (!left) {
          context.addIssue({ code: 'custom', message: 'Поле отсутствует в Rule Schema', path: [group, index, 'left', 'field'] });
          return;
        }
        if (!left.allowedOperators.includes(expression.operator)) {
          context.addIssue({ code: 'custom', message: 'Оператор недоступен для выбранного поля', path: [group, index, 'operator'] });
        }
        if (expression.right.type === 'FIELD') {
          const right = findField(schema, expression.right.source, expression.right.field);
          if (!right) context.addIssue({ code: 'custom', message: 'Выберите поле для сравнения', path: [group, index, 'right', 'field'] });
          else if (right.dataType !== left.dataType) context.addIssue({ code: 'custom', message: 'Типы полей несовместимы', path: [group, index, 'right', 'field'] });
        } else {
          const message = validateConstant(left, expression);
          if (message) context.addIssue({ code: 'custom', message, path: [group, index, 'right', 'value'] });
        }
      });
    }
  });
}

export type RuleDraftForm = RuleDraft;
