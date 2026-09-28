import { useState } from 'react';
import { Input } from '../Input';
import { Button } from '../Button';

interface Props {
    values: Array<string | number>;
    onChange: (v: Array<string | number>) => void;
    invalid?: boolean;
    disabled?: boolean;
    minItems?: number;
    maxItems?: number;
    numeric?: boolean;
}

export function MultiValueInput({
    values,
    onChange,
    invalid,
    disabled,
    minItems = 1,
    maxItems,
    numeric = false,
}: Props) {
    const [draft, setDraft] = useState('');

    const add = () => {
        const t = draft.trim();
        if (!t) return;
        if (maxItems !== undefined && values.length >= maxItems) return;

        const value: string | number = numeric ? Number(t) : t;
        if (numeric && !Number.isFinite(value as number)) return;

        onChange([...values, value]);
        setDraft('');
    };

    const remove = (idx: number) => {
        onChange(values.filter((_, i) => i !== idx));
    };

    const canAdd =
        !disabled &&
        draft.trim().length > 0 &&
        (maxItems === undefined || values.length < maxItems);

    return (
        <div className="multi-value">
            <div className="multi-value-list">
                {values.map((v, i) => (
                    <span key={`${v}-${i}`} className="multi-value-item">
                        {v}
                        <button
                            type="button"
                            onClick={() => remove(i)}
                            disabled={disabled || values.length <= minItems}
                            aria-label="Удалить"
                        >
                            ×
                        </button>
                    </span>
                ))}
            </div>
            <div className="multi-value-add">
                <Input
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    invalid={invalid}
                    disabled={disabled || (maxItems !== undefined && values.length >= maxItems)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                            e.preventDefault();
                            add();
                        }
                    }}
                />
                <Button type="button" variant="secondary" onClick={add} disabled={!canAdd}>
                    Добавить
                </Button>
            </div>
        </div>
    );
}