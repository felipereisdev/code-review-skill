import { getPrice } from './pricing';

export interface PaymentGateway {
  charge(amountCents: number): Promise<string>;
}

/** Charges the customer for `quantity` units of `sku` and returns the charge id. */
export async function checkout(gateway: PaymentGateway, sku: string, quantity: number): Promise<string> {
  const amountCents = getPrice(sku) * quantity;
  return gateway.charge(amountCents);
}
