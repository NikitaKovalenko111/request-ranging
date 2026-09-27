import { type ReactNode, useEffect } from 'react';
import { Button } from './Button';

interface Props {
    open: boolean;
    title: string;
    onClose: () => void;
    children: ReactNode;
}

export function Drawer({ open, title, onClose, children }: Props) {
    useEffect(() => {
        if (!open) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [open, onClose]);

    if (!open) return null;

    return (
        <div className="drawer-backdrop" onClick={onClose}>
            <div
                className="drawer"
                role="dialog"
                aria-modal="true"
                aria-label={title}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="drawer-header">
                    <h2>{title}</h2>
                    <Button variant="ghost" onClick={onClose}>×</Button>
                </div>
                <div className="drawer-body">{children}</div>
            </div>
        </div>
    );
}