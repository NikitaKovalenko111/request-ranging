import type { OrderOption } from '../types/order';

export const mockOrderOptions: OrderOption[] = [
    { id: '1032', label: 'Заявка #1032 — VIP', status: 'processed', vip: true },
    { id: '1033', label: 'Заявка #1033', status: 'await', vip: false },
    { id: '1034', label: 'Заявка #1034', status: 'processed', vip: false },
    { id: '1035', label: 'Заявка #1035 — VIP', status: 'accept', vip: true },
];
