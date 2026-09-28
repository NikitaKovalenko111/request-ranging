import { describe, expect, it } from 'vitest';
import { formatDuration } from '.';

describe('formatDuration', () => {
  it('показывает короткое время в миллисекундах и округляет дробь', () => {
    expect(formatDuration(48.1234)).toBe('48,12 мс');
  });

  it('переводит значения от одной секунды в секунды', () => {
    expect(formatDuration(1500)).toBe('1,5 с');
  });

  it('обрабатывает отсутствие значения', () => {
    expect(formatDuration(null)).toBe('Нет данных');
  });
});
