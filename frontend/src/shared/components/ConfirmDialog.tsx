import { Dialog } from './Dialog';
import { Button } from './Button';

interface Props {
    open: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    loading?: boolean;
    onConfirm: () => void;
    onCancel: () => void;
}

export function ConfirmDialog({
    open, title, message, confirmLabel = 'Подтвердить', loading, onConfirm, onCancel,
}: Props) {
    return (
        <Dialog open={open} title={title} onClose={onCancel}>
            <p>{message}</p>
            <div className="dialog-actions">
                <Button variant="secondary" onClick={onCancel}>Отмена</Button>
                <Button variant="danger" loading={loading} onClick={onConfirm}>{confirmLabel}</Button>
            </div>
        </Dialog>
    );
}
