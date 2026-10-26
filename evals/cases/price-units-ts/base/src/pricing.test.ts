import { describe, expect, it } from 'vitest';
import { getPrice } from './pricing';

describe('getPrice', () => {
  it('returns the unit price in cents', () => {
    expect(getPrice('mug')).toBe(1250);
  });

  it('rejects an unknown sku', () => {
    expect(() => getPrice('hat')).toThrow('unknown sku: hat');
  });
});
