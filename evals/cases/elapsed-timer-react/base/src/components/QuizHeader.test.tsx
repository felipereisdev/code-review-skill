import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { QuizHeader } from './QuizHeader';

describe('QuizHeader', () => {
  it('shows the quiz title', () => {
    render(<QuizHeader title="Capitals" />);
    expect(screen.getByRole('heading', { name: 'Capitals' })).toBeTruthy();
  });
});
