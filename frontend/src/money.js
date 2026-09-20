// The API sends Decimal prices as strings with two fractional digits.
export function toCents(price) {
  const [whole, fraction = ''] = price.split('.')
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0').slice(0, 2))
}

export function formatCents(cents) {
  return `$${cents / 100n}.${(cents % 100n).toString().padStart(2, '0')}`
}
