export interface PaymentGateway {
  charge(customerId: string, amountCents: number): Promise<{ id: string }>;
}

export type ChargeResult = { ok: true; chargeId: string } | { ok: false; error: string };

export async function chargeInvoice(
  gateway: PaymentGateway,
  customerId: string,
  amountCents: number,
): Promise<ChargeResult> {
  const charge = await gateway.charge(customerId, amountCents);
  return { ok: true, chargeId: charge.id };
}
