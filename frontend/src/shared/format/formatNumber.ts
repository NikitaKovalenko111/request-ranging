export function formatNumber(value: number | null | undefined, digits = 2): string {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    const fixed = value.toFixed(digits);
    return fixed.replace(/\.?0+$/, '') || '0';
}