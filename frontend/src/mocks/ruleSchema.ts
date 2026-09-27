import type { RuleSchema } from '../types/ruleSchema';

export const mockRuleSchema: RuleSchema = {
    version: '1',
    orderFields: [
        {
            source: 'ORDER',
            name: 'vip',
            label: 'VIP',
            dataType: 'BOOLEAN',
            nullable: false,
            allowedOperators: ['EQ', 'NE'],
        },
        {
            source: 'ORDER',
            name: 'sum',
            label: 'Сумма заявки',
            dataType: 'NUMBER',
            nullable: true,
            allowedOperators: ['EQ', 'NE', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN'],
        },
        {
            source: 'ORDER',
            name: 'orderType',
            label: 'Тип заявки',
            dataType: 'ENUM',
            nullable: false,
            allowedOperators: ['EQ', 'NE', 'IN', 'NOT_IN'],
            options: [
                { value: 'ORDER_1', label: 'Тип 1' },
                { value: 'ORDER_2', label: 'Тип 2' },
            ],
        },
        {
            source: 'ORDER',
            name: 'subject',
            label: 'Тема',
            dataType: 'STRING',
            nullable: true,
            allowedOperators: ['EQ', 'NE', 'CONTAINS'],
        },
        {
            source: 'ORDER',
            name: 'weight',
            label: 'Вес заявки',
            dataType: 'NUMBER',
            nullable: false,
            allowedOperators: ['EQ', 'NE', 'GT', 'GTE', 'LT', 'LTE'],
        },
    ],
    executorFields: [
        {
            source: 'EXECUTOR',
            name: 'qualification',
            label: 'Квалификация',
            dataType: 'ENUM',
            nullable: true,
            allowedOperators: ['EQ', 'NE', 'IN', 'NOT_IN'],
            options: [
                { value: 'JUNIOR', label: 'Junior' },
                { value: 'MIDDLE', label: 'Middle' },
                { value: 'SENIOR', label: 'Senior' },
            ],
        },
        {
            source: 'EXECUTOR',
            name: 'capacityWeight',
            label: 'Вес исполнителя',
            dataType: 'NUMBER',
            nullable: false,
            allowedOperators: ['EQ', 'NE', 'GT', 'GTE', 'LT', 'LTE'],
        },
        {
            source: 'EXECUTOR',
            name: 'maxAcceptSum',
            label: 'Максимальная сумма',
            dataType: 'NUMBER',
            nullable: true,
            allowedOperators: ['EQ', 'NE', 'GT', 'GTE', 'LT', 'LTE'],
        },
    ],
};