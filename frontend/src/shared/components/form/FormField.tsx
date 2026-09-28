import type { ReactNode } from 'react';

interface Props {
    label: string;
    htmlFor?: string;
    error?: string;
    required?: boolean;
    hint?: string;
    children: ReactNode;
}

export function FormField({ label, htmlFor, error, required, hint, children }: Props) {
    return (
        <div className="form-field">
            <label htmlFor={htmlFor} className="form-label">
                {label}
                {required ? ' *' : ''}
            </label>
            {children}
            {hint ? <div className="form-hint">{hint}</div> : null}
            {error ? <div className="form-error" role="alert">{error}</div> : null}
        </div>
    );
}