import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { QuizHeader } from './QuizHeader';

afterEach(() => {
  cleanup();
});

describe('QuizHeader', () => {
  it('shows the quiz title', () => {
    render(<QuizHeader title="Capitals" />);
    expect(screen.getByRole('heading', { name: 'Capitals' })).toBeTruthy();
  });
});
