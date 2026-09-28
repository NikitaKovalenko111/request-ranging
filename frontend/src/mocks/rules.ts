import type { Rule } from '../types/rule';

export const mockRules: Rule[] = [
  {
    id: 'rule-vip-senior',
    name: 'VIP только для Senior',
    description: 'VIP-заявки допускаются только к старшим специалистам',
    when: [
      {
        left: { type: 'FIELD', source: 'ORDER', field: 'vip' },
        operator: 'EQ',
        right: { type: 'CONSTANT', value: true },
      },
    ],
    requirements: [
      {
        left: { type: 'FIELD', source: 'EXECUTOR', field: 'qualification' },
        operator: 'EQ',
        right: { type: 'CONSTANT', value: 'SENIOR' },
      },
    ],
    logic: 'AND',
    priority: 10,
    active: true,
    createdAt: '2026-09-25T10:00:00Z',
    updatedAt: '2026-09-25T12:00:00Z',
    version: 3,
  },
  {
    id: 'rule-max-sum',
    name: 'Ограничение максимальной суммы',
    description: null,
    when: [],
    requirements: [
      {
        left: { type: 'FIELD', source: 'ORDER', field: 'sum' },
        operator: 'LTE',
        right: { type: 'FIELD', source: 'EXECUTOR', field: 'maxAcceptSum' },
      },
    ],
    logic: 'AND',
    priority: 20,
    active: true,
    createdAt: '2026-09-24T10:00:00Z',
    updatedAt: '2026-09-24T10:00:00Z',
    version: 1,
  },
  {
    id: 'rule-order-type-in',
    name: 'Типы заявок',
    description: 'Допускаются только типы 1 и 2',
    when: [],
    requirements: [
      {
        left: { type: 'FIELD', source: 'ORDER', field: 'orderType' },
        operator: 'IN',
        right: { type: 'CONSTANT', value: ['ORDER_1', 'ORDER_2'] },
      },
    ],
    logic: 'AND',
    priority: 30,
    active: false,
    createdAt: '2026-09-23T10:00:00Z',
    updatedAt: '2026-09-23T10:00:00Z',
    version: 1,
  },
  {
    id: 'rule-between',
    name: 'Сумма от 1000 до 5000',
    description: 'Правило применяется к заявкам со суммой в диапазоне',
    when: [],
    requirements: [
      {
        left: { type: 'FIELD', source: 'ORDER', field: 'sum' },
        operator: 'BETWEEN',
        right: { type: 'CONSTANT', value: [1000, 5000] },
      },
    ],
    logic: 'AND',
    priority: 40,
    active: true,
    createdAt: '2026-09-22T10:00:00Z',
    updatedAt: '2026-09-22T10:00:00Z',
    version: 1,
  },
  {
    id: 'rule-not-in',
    name: 'Исключить типы',
    description: 'Тип заявки не должен быть ORDER_3',
    when: [],
    requirements: [
      {
        left: { type: 'FIELD', source: 'ORDER', field: 'orderType' },
        operator: 'NOT_IN',
        right: { type: 'CONSTANT', value: ['ORDER_3'] },
      },
    ],
    logic: 'AND',
    priority: 50,
    active: true,
    createdAt: '2026-09-22T11:00:00Z',
    updatedAt: '2026-09-22T11:00:00Z',
    version: 1,
  },
];