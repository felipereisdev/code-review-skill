import { describe, expect, it } from 'vitest';
import { chargeInvoice, type PaymentGateway } from '../src/charge';

const okGateway: PaymentGateway = {
  charge: async () => ({ id: 'ch_123' }),
};

describe('chargeInvoice', () => {
  it('returns the charge id on success', async () => {
    await expect(chargeInvoice(okGateway, 'cus_1', 500)).resolves.toEqual({ ok: true, chargeId: 'ch_123' });
  });
});
