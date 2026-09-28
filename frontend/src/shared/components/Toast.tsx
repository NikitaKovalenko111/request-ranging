import {
    createContext,
    useCallback,
    useContext,
    useState,
    type ReactNode,
} from 'react';

interface ToastItem {
    id: number;
    message: string;
    tone: 'success' | 'error' | 'info';
}

interface ToastContextValue {
    show: (message: string, tone?: ToastItem['tone']) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
    const [items, setItems] = useState<ToastItem[]>([]);

    const show = useCallback((message: string, tone: ToastItem['tone'] = 'info') => {
        const id = Date.now() + Math.random();
        setItems((prev) => [...prev, { id, message, tone }]);
        window.setTimeout(() => {
            setItems((prev) => prev.filter((t) => t.id !== id));
        }, 3000);
    }, []);

    return (
        <ToastContext.Provider value={{ show }}>
            {children}
            <div className="toast-stack" aria-live="polite">
                {items.map((t) => (
                    <div key={t.id} className={`toast toast-${t.tone}`} role="status">
                        {t.message}
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}

export function useToast() {
    const ctx = useContext(ToastContext);
    if (!ctx) throw new Error('useToast must be used within ToastProvider');
    return ctx;
}