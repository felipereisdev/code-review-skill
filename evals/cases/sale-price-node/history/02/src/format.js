'use strict';

function formatPrice(amount) {
  if (amount == null) {
    return '—';
  }
  return `$${amount.toFixed(2)}`;
}

module.exports = { formatPrice };
