import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: Variant;
    loading?: boolean;
}

export function Button({
    variant = 'primary',
    loading,
    children,
    disabled,
    className,
    ...rest
}: Props) {
    return (
        <button
            {...rest}
            disabled={disabled || loading}
            className={`button ${variant} ${className ?? ''}`}
        >
            {loading ? '…' : children}
        </button>
    );
}