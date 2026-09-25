import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusBadge } from './StatusBadge';

describe('StatusBadge', () => {
  it('показывает статус текстом, а не только цветом', () => {
    render(<StatusBadge status="assigned" />);
    expect(screen.getByText('Назначена')).toBeInTheDocument();
  });
});
