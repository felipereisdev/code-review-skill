'use strict';

const { formatPrice } = require('./format');

function cartRows(items) {
  return items.map((item) => ({
    name: item.name,
    price: formatPrice(item.price),
    sale: formatPrice(item.salePrice),
  }));
}

module.exports = { cartRows };
