export interface Product {
  sku: string;
  name: string;
  priceCents: number;
}

export const products: Product[] = [
  { sku: 'mug', name: 'Coffee mug', priceCents: 1250 },
  { sku: 'tee', name: 'T-shirt', priceCents: 2000 },
];
