import type { ReactNode } from 'react';

interface Props {
    open: boolean;
    title: string;
    onClose: () => void;
    children: ReactNode;
}

export function Dialog({ open, title, onClose, children }: Props) {
    if (!open) return null;
    return (
        <div className="dialog-backdrop" onClick={onClose}>
            <div className="dialog" onClick={(e) => e.stopPropagation()}>
                <header className="dialog-header">
                    <h2>{title}</h2>
                    <Button variant="ghost" onClick={onClose}>×</Button>
                </header>
                <div className="dialog-body">{children}</div>
            </div>
        </div>
    );
}

import { Button } from './Button';