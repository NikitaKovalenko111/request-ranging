import { Button } from '../../../shared/components/Button';

export function RulePriorityControl({
    value,
    onChange,
    disabled,
}: {
    value: number;
    onChange: (v: number) => void;
    disabled?: boolean;
}) {
    return (
        <div className="priority-control">
            <Button
                variant="ghost"
                disabled={disabled || value <= 0}
                onClick={() => onChange(Math.max(0, value - 10))}
                aria-label="Уменьшить приоритет"
            >
                ↓
            </Button>
            <strong>{value}</strong>
            <Button
                variant="ghost"
                disabled={disabled}
                onClick={() => onChange(value + 10)}
                aria-label="Увеличить приоритет"
            >
                ↑
            </Button>
        </div>
    );
}