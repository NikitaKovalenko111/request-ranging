import { CheckCircle2, FlaskConical, Power } from 'lucide-react';
import type { ApiError } from '../../../types/api';
import { ErrorState, LoadingState } from '../../../shared/components/StateViews';
import { formatDateTime } from '../../../shared/format';
import { useOrderOptions } from '../../orders/hooks/useOrders';
import { useRules, useSetRuleActive, useTestRules } from '../hooks/useRules';

export function RulesPage() {
  const query = useRules();
  const orders = useOrderOptions();
  const mutation = useSetRuleActive();
  const testMutation = useTestRules();
  if (query.isLoading) return <LoadingState rows={4} />;
  if (query.isError) return <ErrorState message={(query.error as unknown as ApiError).message} onRetry={() => void query.refetch()} />;
  return <div className="page-stack"><div className="page-actions"><div><h2 className="page-lead">Правила распределения</h2><p>Порядок hard rules и быстрая проверка на демонстрационной заявке.</p></div><span className="summary-chip"><CheckCircle2 size={16} />Активны {(query.data ?? []).filter((rule) => rule.active).length}</span></div><div className="rules-layout"><section className="rule-list">{(query.data ?? []).sort((a, b) => a.priority - b.priority).map((rule) => <article className="panel rule-card" key={rule.id}><div><span className="rule-priority">P{rule.priority}</span><h2>{rule.name}</h2><p>{rule.description}</p><code>{rule.condition}</code><small>Обновлено: {formatDateTime(rule.updatedAt)}</small></div><button className={`toggle-button ${rule.active ? 'on' : ''}`} aria-pressed={rule.active} disabled={mutation.isPending} onClick={() => mutation.mutate({ id: rule.id, active: !rule.active })}><span /><Power size={14} />{rule.active ? 'Включено' : 'Выключено'}</button></article>)}</section><aside className="panel rule-test"><FlaskConical /><span className="section-kicker">Test Rule</span><h2>Проверка заявки</h2><p>Выберите заявку — Rule Engine вернёт число прошедших и исключённых кандидатов.</p><select aria-label="Заявка для проверки" defaultValue="" onChange={(event) => { if (event.target.value) testMutation.mutate(Number(event.target.value)); }}><option value="">Выберите заявку</option>{orders.data?.items.map((order) => <option value={order.id} key={order.id}>{order.label}{order.vip ? ' · VIP' : ''}</option>)}</select>{testMutation.isPending && <div className="test-result"><FlaskConical /><div><strong>Проверяем…</strong><span>Выполняются активные правила.</span></div></div>}{testMutation.data && <div className="test-result"><CheckCircle2 /><div><strong>{testMutation.data.eligibleExecutors} из {testMutation.data.totalExecutors} прошли</strong><span>{testMutation.data.explanation} Исключено: {testMutation.data.rejectedExecutors}.</span></div></div>}</aside></div></div>;
}
