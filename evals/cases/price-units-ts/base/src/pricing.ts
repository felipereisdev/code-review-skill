import { products } from './catalog';

/** Returns the price of one unit of `sku` in cents. */
export function getPrice(sku: string): number {
  const product = products.find((p) => p.sku === sku);
  if (!product) {
    throw new Error(`unknown sku: ${sku}`);
  }
  return product.priceCents;
}
