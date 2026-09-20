// The API sends Decimal prices as strings with two fractional digits.
export function toCents(price) {
  const [whole, fraction = ''] = price.split('.')
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0').slice(0, 2))
}

function groupThousands(digits) {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

export function formatCents(cents) {
  const sign = cents < 0n ? '-' : ''
  const absolute = cents < 0n ? -cents : cents
  return `${sign}$${groupThousands((absolute / 100n).toString())},${(absolute % 100n).toString().padStart(2, '0')}`
}

export function formatPrice(price) {
  return formatCents(toCents(price))
}

// Keep the decimal point for HTML number inputs and API requests.
export function compactDecimal(value) {
  const [whole, fraction = ''] = String(value).split('.')
  const significantFraction = fraction.replace(/0+$/, '')
  return significantFraction ? `${whole}.${significantFraction}` : whole
}

export function formatQuantity(value) {
  const [whole, fraction] = compactDecimal(value).split('.')
  return `${groupThousands(whole)}${fraction ? `,${fraction}` : ''}`
}
