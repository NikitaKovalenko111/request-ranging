import { Select } from '../Select';

interface Props {
    value: boolean | null;
    onChange: (v: boolean) => void;
    invalid?: boolean;
    disabled?: boolean;
}

export function BooleanSelect({ value, onChange, invalid, disabled }: Props) {
    return (
        <Select
            value={value === null ? '' : value ? 'true' : 'false'}
            onChange={(e) => onChange(e.target.value === 'true')}
            invalid={invalid}
            disabled={disabled}
        >
            <option value="">— выберите —</option>
            <option value="true">Да</option>
            <option value="false">Нет</option>
        </Select>
    );
}