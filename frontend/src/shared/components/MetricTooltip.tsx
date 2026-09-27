import { CircleHelp } from 'lucide-react';

export function MetricTooltip({ text }: { text: string }) {
  return <span className="metric-tooltip" tabIndex={0} aria-label={text}><CircleHelp size={15} aria-hidden="true" /><span role="tooltip">{text}</span></span>;
}

