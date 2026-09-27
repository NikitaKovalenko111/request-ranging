import { forwardRef } from 'react';
import { Input } from '../Input';

interface Props {
    value: number | null;
    onChange: (v: number | null) => void;
    invalid?: boolean;
    disabled?: boolean;
    placeholder?: string;
    min?: number;
    max?: number;
}

export const NumberField = forwardRef<HTMLInputElement, Props>(function NumberField(
    { value, onChange, invalid, disabled, placeholder, min, max },
    ref,
) {
    return (
        <Input
            ref={ref}
            type="number"
            value={value === null ? '' : value}
            min={min}
            max={max}
            onChange={(e) => {
                const raw = e.target.value;
                if (raw === '') return onChange(null);
                const n = Number(raw);
                onChange(Number.isFinite(n) ? n : null);
            }}
            invalid={invalid}
            disabled={disabled}
            placeholder={placeholder}
        />
    );
});