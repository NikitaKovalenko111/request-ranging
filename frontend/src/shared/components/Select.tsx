import { forwardRef, type SelectHTMLAttributes, type ReactNode } from 'react';

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
    invalid?: boolean;
    children: ReactNode;
}

export const Select = forwardRef<HTMLSelectElement, Props>(function Select(
    { invalid, className, children, ...rest },
    ref,
) {
    return (
        <select
            {...rest}
            ref={ref}
            aria-invalid={invalid ? 'true' : undefined}
            className={`select ${invalid ? 'select-invalid' : ''} ${className ?? ''}`}
        >
            {children}
        </select>
    );
});