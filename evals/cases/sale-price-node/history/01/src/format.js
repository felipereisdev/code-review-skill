'use strict';

function formatPrice(amount) {
  return `$${amount.toFixed(2)}`;
}

module.exports = { formatPrice };
