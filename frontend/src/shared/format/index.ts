const ruNumber = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 });
const ruMoney = new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
const ruDateTime = new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' });

export const formatNumber = (value: number | null | undefined) => value == null ? 'Нет данных' : ruNumber.format(value);
export const formatMoney = (value: number | null | undefined) => value == null ? 'Не указана' : ruMoney.format(value);
export const formatDateTime = (value: string | null | undefined) => value ? ruDateTime.format(new Date(value)) : 'Нет данных';
export const formatDuration = (value: number | null | undefined) => value == null ? 'Нет данных' : value < 1000 ? `${formatNumber(value)} мс` : `${formatNumber(value / 1000)} с`;
export const formatPercent = (value: number | null | undefined) => value == null ? 'Нет данных' : `${ruNumber.format(value * 100)}%`;
export const formatBoolean = (value: boolean | null | undefined) => value == null ? 'Нет данных' : value ? 'Да' : 'Нет';

