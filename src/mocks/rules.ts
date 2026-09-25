import type { RuleSummary } from '../types/rule';

export const mockRules: RuleSummary[] = [
  { id: 'rule-active', name: 'Активность исполнителя', description: 'Исключает неактивных исполнителей.', active: true, priority: 10, condition: 'executor.status == ACTIVE', updatedAt: new Date().toISOString() },
  { id: 'rule-daily-limit', name: 'Суточный лимит', description: 'Проверяет количество назначений за текущие сутки.', active: true, priority: 20, condition: 'dailyCount < maxDailyLimit', updatedAt: new Date().toISOString() },
  { id: 'rule-qualification', name: 'Профиль компетенций', description: 'Сопоставляет тематику заявки и квалификацию.', active: true, priority: 30, condition: 'qualification includes order.subject', updatedAt: new Date().toISOString() },
  { id: 'rule-vip', name: 'VIP-маршрутизация', description: 'Разрешает VIP-заявки исполнителям с повышенным весом.', active: false, priority: 40, condition: '!order.vip || capacityWeight >= 1.5', updatedAt: new Date().toISOString() },
];

