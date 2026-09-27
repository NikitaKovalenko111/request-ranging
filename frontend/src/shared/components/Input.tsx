import { forwardRef, type InputHTMLAttributes } from 'react';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
    invalid?: boolean;
}

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
    { invalid, className, ...rest },
    ref,
) {
    return (
        <input
            {...rest}
            ref={ref}
            aria-invalid={invalid ? 'true' : undefined}
            className={`input ${invalid ? 'input-invalid' : ''} ${className ?? ''}`}
        />
    );
});