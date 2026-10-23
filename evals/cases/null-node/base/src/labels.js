'use strict';

const customers = new Map([
  [1, { name: 'Ada Lovelace', address: { street: '12 St James Sq', city: 'London' } }],
  [2, { name: 'Alan Turing', address: { street: '78 High St', city: 'Wilmslow' } }],
]);

function shippingLabel(order) {
  const customer = customers.get(order.customerId);
  if (!customer) {
    return null;
  }
  return [customer.name, customer.address.street, customer.address.city].join('\n');
}

module.exports = { shippingLabel, customers };
