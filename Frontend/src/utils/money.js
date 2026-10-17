// Arithmetic uses integer cents; division is only for display.
export function parseEUR(value) {
  const text = String(value).trim();
  if (!/^\d+(?:\.\d{1,2})?$/.test(text)) return null;
  const [whole, fraction = ''] = text.split('.');
  const result = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
  return Number.isSafeInteger(result) && result <= 100000000 ? result : null;
}
export function priceCents(product) {
  const result = product.price_cents ?? parseEUR(product.price);
  if (!Number.isSafeInteger(result) || result < 0) throw new Error('Invalid catalog price');
  return result;
}
export function formatEUR(value) {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error('Invalid EUR total');
  return new Intl.NumberFormat('en-IE', {style: 'currency', currency: 'EUR'}).format(value / 100);
}
