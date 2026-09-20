import assert from 'node:assert/strict'
import test from 'node:test'
import { formatCents, toCents } from './money.js'

test('partial payment preview sums historical prices exactly in cents', () => {
  const total = ['12000.50', '9000.00', '0.05'].reduce((sum, price) => sum + toCents(price), 0n)
  assert.equal(formatCents(total), '$21000.55')
})
