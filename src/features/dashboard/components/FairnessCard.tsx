import { Scale } from 'lucide-react';
import type { DashboardData } from '../../../types/dashboard';
import { formatDateTime, formatPercent } from '../../../shared/format';

export function FairnessCard({ data }: { data: DashboardData }) {
  const { fairness, summary } = data;
  const value = fairness.kind === 'JAIN_INDEX' ? fairness.value.toFixed(3) : formatPercent(fairness.value);
  const target = fairness.target == null ? 'Не задана' : fairness.kind === 'JAIN_INDEX' ? fairness.target.toFixed(3) : formatPercent(fairness.target);
  return <section className="panel fairness-card"><div className="fairness-icon"><Scale /></div><span className="section-kicker">{fairness.kind === 'JAIN_INDEX' ? 'Jain Index' : 'Отклонение нагрузки'}</span><div className="fairness-value">{value}</div><div className="target-line"><span>Цель</span><strong>{target}</strong></div><p>{fairness.description}</p><small>Период: {formatDateTime(summary.periodFrom)} — {formatDateTime(summary.periodTo)}</small></section>;
}

