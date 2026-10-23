import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { CommentList } from './CommentList';

describe('CommentList', () => {
  it('shows each author', () => {
    render(<CommentList comments={[{ id: 1, author: 'Ada', body: 'Hello' }]} />);
    expect(screen.getByText('Ada')).toBeTruthy();
  });
});
