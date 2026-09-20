import assert from 'node:assert/strict'
import test from 'node:test'
import { compactDecimal, formatCents, formatPrice, formatQuantity, toCents } from './money.js'

test('partial payment preview sums historical prices exactly in cents', () => {
  const total = ['12000.50', '9000.00', '0.05'].reduce((sum, price) => sum + toCents(price), 0n)
  assert.equal(formatCents(total), '$21.000,55')
})

test('prices use thousands points and exactly two decimal digits', () => {
  assert.equal(formatPrice('16000.00'), '$16.000,00')
  assert.equal(formatPrice('1234567.50'), '$1.234.567,50')
  assert.equal(formatPrice('0.05'), '$0,05')
})

test('ingredient quantities omit insignificant decimal zeros', () => {
  assert.equal(formatQuantity('20.000'), '20')
  assert.equal(formatQuantity('20.500'), '20,5')
  assert.equal(formatQuantity('1234.250'), '1.234,25')
  assert.equal(compactDecimal('20.500'), '20.5')
})
