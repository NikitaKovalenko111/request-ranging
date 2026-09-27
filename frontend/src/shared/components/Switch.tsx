interface Props {
    checked: boolean;
    onChange: (checked: boolean) => void;
    disabled?: boolean;
    label?: string;
    id?: string;
}

export function Switch({ checked, onChange, disabled, label, id }: Props) {
    return (
        <label className="switch" htmlFor={id}>
            <input
                id={id}
                type="checkbox"
                role="switch"
                checked={checked}
                disabled={disabled}
                onChange={(e) => onChange(e.target.checked)}
            />
            <span className="switch-slider" aria-hidden="true" />
            {label ? <span className="switch-label">{label}</span> : null}
        </label>
    );
}