import type { LucideIcon } from 'lucide-react';
import { MetricTooltip } from '../../../shared/components/MetricTooltip';

export function KpiCard({ label, value, unit, icon: Icon, tone = 'blue', hint }: { label: string; value: string; unit?: string; icon: LucideIcon; tone?: string; hint?: string }) {
  return <article className={`kpi-card tone-${tone}`}><div className="kpi-top"><span className="kpi-icon"><Icon size={19} /></span>{hint && <MetricTooltip text={hint} />}</div><div className="kpi-value">{value}{unit && <span>{unit}</span>}</div><p>{label}</p></article>;
}

