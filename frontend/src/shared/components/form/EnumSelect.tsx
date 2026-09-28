import { Select } from '../Select';
import type { RuleFieldOption } from '../../../types/ruleSchema';

interface Props {
    value: string | number | boolean | null;
    onChange: (v: string | number | boolean) => void;
    options: RuleFieldOption[];
    invalid?: boolean;
    disabled?: boolean;
}

export function EnumSelect({ value, onChange, options, invalid, disabled }: Props) {
    return (
        <Select
            value={value === null ? '' : String(value)}
            onChange={(e) => {
                const raw = e.target.value;
                const opt = options.find((o) => String(o.value) === raw);
                if (opt) onChange(opt.value);
            }}
            invalid={invalid}
            disabled={disabled}
        >
            <option value="">— выберите —</option>
            {options.map((o) => (
                <option key={String(o.value)} value={String(o.value)}>
                    {o.label}
                </option>
            ))}
        </Select>
    );
}