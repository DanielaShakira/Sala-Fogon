import assert from 'node:assert/strict'
import test from 'node:test'
import { createLatestRequestGuard } from './latestRequest.js'

test('changing sessions invalidates the old response and clears its authority', () => {
  const guard = createLatestRequestGuard()
  guard.select(1)
  const firstResponseIsCurrent = guard.begin(1)
  guard.select(2)
  const secondResponseIsCurrent = guard.begin(2)
  assert.equal(firstResponseIsCurrent(), false)
  assert.equal(secondResponseIsCurrent(), true)
  assert.equal(guard.current(), 2)
})

test('a newer refresh wins even for the same session', () => {
  const guard = createLatestRequestGuard()
  guard.select(1)
  const oldResponseIsCurrent = guard.begin(1)
  const newResponseIsCurrent = guard.begin(1)
  assert.equal(oldResponseIsCurrent(), false)
  assert.equal(newResponseIsCurrent(), true)
})

test('cancellation invalidates an in-flight read until the next refresh', () => {
  const guard = createLatestRequestGuard()
  guard.select(1)
  const beforeCancellation = guard.begin(1)
  guard.invalidate()
  assert.equal(beforeCancellation(), false)
  const afterCancellation = guard.begin(1)
  assert.equal(afterCancellation(), true)
  guard.select(null)
  assert.equal(afterCancellation(), false)
})
