import test from 'node:test'
import assert from 'node:assert/strict'
import { createReadyTracker, mensajeItemsListos } from './readyNotifications.js'

function pedido(sesion, mesa, numero, items) {
  return {
    sesion_id: sesion, mesa_numero: mesa, numero_en_sesion: numero,
    items: items.map(([id, plato, estado]) => ({ id, plato, estado })),
  }
}

test('solo avisa de una transición observada hacia LISTO y no repite el aviso', () => {
  const tracker = createReadyTracker()
  const enCola = [pedido(1, 10, 1, [[1, 'Sopa', 'EN_COLA']])]
  assert.deepEqual(tracker.observe(enCola), [])
  const listo = [pedido(1, 10, 1, [[1, 'Sopa', 'LISTO']])]
  assert.deepEqual(tracker.observe(listo), [
    { id: 1, plato: 'Sopa', mesa: 10, pedido: 1 },
  ])
  assert.deepEqual(tracker.observe(listo), [])
})

test('no avisa por estados listos al entrar, recargar o descubrir un ítem nuevo', () => {
  const tracker = createReadyTracker()
  const historico = [pedido(1, 10, 1, [[1, 'Sopa', 'LISTO']])]
  assert.deepEqual(tracker.observe(historico), [])
  assert.deepEqual(tracker.observe([
    ...historico, pedido(2, 11, 1, [[2, 'Arroz', 'LISTO']]),
  ]), [])
  tracker.reset()
  assert.deepEqual(tracker.observe(historico), [])
})

test('sigue todas las mesas propias y agrupa varios ítems listos en un aviso', () => {
  const tracker = createReadyTracker()
  tracker.observe([
    pedido(1, 10, 1, [[1, 'Sopa', 'EN_COLA'], [2, 'Sopa', 'EN_PREPARACION']]),
    pedido(2, 11, 1, [[3, 'Arroz', 'EN_PREPARACION']]),
  ])
  const cambios = tracker.observe([
    pedido(1, 10, 1, [[1, 'Sopa', 'LISTO'], [2, 'Sopa', 'LISTO']]),
    pedido(2, 11, 1, [[3, 'Arroz', 'LISTO']]),
  ])
  assert.equal(cambios.length, 3)
  assert.equal(mensajeItemsListos(cambios),
    '3 platos listos: Sopa ×2 (mesa 10, pedido 1); Arroz (mesa 11, pedido 1).')
})

test('no interpreta una cancelación ni la desaparición de una sesión como un plato listo', () => {
  const tracker = createReadyTracker()
  tracker.observe([pedido(1, 10, 1, [[1, 'Sopa', 'EN_COLA']])])
  assert.deepEqual(tracker.observe([pedido(1, 10, 1, [[1, 'Sopa', 'CANCELADO']])]), [])
  assert.deepEqual(tracker.observe([]), [])
})
