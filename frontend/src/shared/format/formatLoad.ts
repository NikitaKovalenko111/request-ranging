import { formatNumber } from './formatNumber';

export function formatLoad(load: number | null | undefined): string {
    return formatNumber(load, 2);
}

export function formatDailyLimit(
    dailyCount: number,
    maxDailyLimit: number | null,
): string {
    if (maxDailyLimit === null) return `${dailyCount} / Без ограничений`;
    return `${dailyCount} / ${maxDailyLimit}`;
}