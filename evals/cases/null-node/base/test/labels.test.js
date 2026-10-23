'use strict';

const test = require('node:test');
const assert = require('node:assert');
const { shippingLabel } = require('../src/labels');

test('returns null for an unknown customer', () => {
  assert.strictEqual(shippingLabel({ customerId: 99 }), null);
});

test('formats the label', () => {
  assert.strictEqual(shippingLabel({ customerId: 1 }), 'Ada Lovelace\n12 St James Sq\nLondon');
});
