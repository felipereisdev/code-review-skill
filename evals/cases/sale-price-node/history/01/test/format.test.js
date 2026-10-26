'use strict';

const test = require('node:test');
const assert = require('node:assert');
const { formatPrice } = require('../src/format');

test('formats dollars with two decimals', () => {
  assert.strictEqual(formatPrice(4.5), '$4.50');
});
