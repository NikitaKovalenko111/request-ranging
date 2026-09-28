import type { Assignment } from '../types/assignment';
import type { DecisionTrace } from '../types/decisionTrace';
import { mockOrders } from './orders';

export const mockAssignments: Assignment[] = mockOrders.map((order) => ({
  orderId: order.id,
  executorId: order.assignedExecutorId,
  executorName: order.assignedExecutorName,
  status: order.assignmentStatus,
  createdAt: order.createdAt,
  reservedAt: order.assignmentStatus === 'reserved' || order.assignmentStatus === 'assigned' ? order.createdAt : null,
  confirmedAt: order.assignedAt,
  processingTimeMs: order.processingTimeMs,
  explanation: order.explanation,
}));

const commonCandidates = [
  { executorId: '28', executorName: 'Петров И. В.', active: true, passedRules: true, failedRules: [], dailyLimitReached: false, rankScore: 0.91, confirmedWeight: 4, pendingWeight: 1, effectiveLoad: 3.33, reservationResult: 'SUCCESS' as const, selected: true },
  { executorId: '11', executorName: 'Соколова М. А.', active: true, passedRules: true, failedRules: [], dailyLimitReached: false, rankScore: 0.86, confirmedWeight: 6, pendingWeight: 2, effectiveLoad: 4.71, reservationResult: 'CONFLICT' as const, selected: false },
  { executorId: '19', executorName: 'Ким А. Л.', active: true, passedRules: false, failedRules: [{ ruleId: 'rule-qualification', ruleName: 'Профиль компетенций', reason: 'Нет квалификации по международному праву' }, { ruleId: 'rule-sum', ruleName: 'Диапазон суммы', reason: 'Сумма заявки превышает установленный максимум' }], dailyLimitReached: false, rankScore: null, confirmedWeight: 2, pendingWeight: 0, effectiveLoad: 2, reservationResult: 'SKIPPED' as const, selected: false },
  { executorId: '34', executorName: 'Орлова Е. Н.', active: true, passedRules: false, failedRules: [{ ruleId: 'rule-daily-limit', ruleName: 'Суточный лимит', reason: 'Достигнут лимит 40 заявок' }], dailyLimitReached: true, rankScore: null, confirmedWeight: 9, pendingWeight: 0, effectiveLoad: 6, reservationResult: 'SKIPPED' as const, selected: false },
];

const successTrace = (orderId: string): DecisionTrace => ({
  orderId,
  timestamp: new Date().toISOString(),
  processingTimeMs: 48,
  modelVersion: 'ranker-heuristic-1.4',
  rulesVersion: 'rules-2026.09.25',
  totalExecutors: 50,
  activeExecutors: 41,
  eligibleExecutors: 8,
  topKExecutors: 3,
  selectedExecutorId: '28',
  explanation: 'Петров И. В. прошёл обязательные правила, вошёл в Top-K и был выбран после конфликта резервирования у более раннего кандидата благодаря минимальной эффективной нагрузке.',
  stages: [
    { code: 'TOTAL', label: 'Все исполнители', inputCount: 50, outputCount: 50, durationMs: 2 },
    { code: 'ACTIVE', label: 'Активные', inputCount: 50, outputCount: 41, durationMs: 3 },
    { code: 'RULE_ENGINE', label: 'Rule Engine', inputCount: 41, outputCount: 8, durationMs: 14 },
    { code: 'RANKING', label: 'Ranking', inputCount: 8, outputCount: 3, durationMs: 11 },
    { code: 'BALANCING', label: 'Балансировка', inputCount: 3, outputCount: 2, durationMs: 6 },
    { code: 'RESERVATION', label: 'Резервирование', inputCount: 2, outputCount: 1, durationMs: 9 },
    { code: 'ASSIGNMENT', label: 'Назначение', inputCount: 1, outputCount: 1, durationMs: 3 },
  ],
  parentReuse: { attempted: false, parentOrderId: null, previousExecutorId: null, previousExecutorName: null, previousExecutorActive: null, parametersMatched: null, dailyLimitIgnored: false, reused: false, reason: null },
  candidates: commonCandidates,
});

export const mockDecisionTraces: Record<string, DecisionTrace | null> = {
  1048: successTrace('1048'),
  1047: { ...successTrace('1047'), selectedExecutorId: '28', explanation: 'Соколова М. А. соответствует правилам и имеет минимальную эффективную нагрузку среди кандидатов.', candidates: commonCandidates.map((candidate) => ({ ...candidate, selected: candidate.executorId === '11', reservationResult: candidate.executorId === '11' ? 'SUCCESS' : 'SKIPPED' })) },
  1046: { ...successTrace('1046'), processingTimeMs: 36, selectedExecutorId: '7', topKExecutors: null, explanation: 'Предыдущий исполнитель активен и соответствует обязательным параметрам. Заявка возвращена ему по parent_id.', parentReuse: { attempted: true, parentOrderId: '1021', previousExecutorId: '7', previousExecutorName: 'Ахметов Р. С.', previousExecutorActive: true, parametersMatched: true, dailyLimitIgnored: true, reused: true, reason: null }, stages: [{ code: 'TOTAL', label: 'Проверка parent_id', inputCount: 1, outputCount: 1, durationMs: 8 }, { code: 'ASSIGNMENT', label: 'Повторное назначение', inputCount: 1, outputCount: 1, durationMs: 28 }], candidates: [{ ...commonCandidates[0], executorId: '7', executorName: 'Ахметов Р. С.', rankScore: null, effectiveLoad: 2.4 }] },
  1045: null,
  1044: { ...successTrace('1044'), selectedExecutorId: null, eligibleExecutors: 0, topKExecutors: null, explanation: 'Назначение не состоялось: ни один активный исполнитель не прошёл обязательные правила.', stages: successTrace('1044').stages.slice(0, 3).map((stage, index) => index === 2 ? { ...stage, outputCount: 0 } : stage), candidates: commonCandidates.map((candidate) => ({ ...candidate, passedRules: false, selected: false, rankScore: null, reservationResult: 'SKIPPED' })), parentReuse: { attempted: false, parentOrderId: null, previousExecutorId: null, previousExecutorName: null, previousExecutorActive: null, parametersMatched: null, dailyLimitIgnored: false, reused: false, reason: null } },
  1043: { ...successTrace('1043'), selectedExecutorId: null, explanation: 'После конфликта резервирования доступных кандидатов не осталось.', candidates: commonCandidates.map((candidate, index) => ({ ...candidate, selected: false, reservationResult: index < 2 ? 'CONFLICT' : 'SKIPPED' })) },
  1021: successTrace('1021'),
};

