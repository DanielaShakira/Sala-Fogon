import test from 'node:test'
import assert from 'node:assert/strict'
import { api, mensajeErrorApi } from './api.js'

test('muestra el motivo del rechazo de un pedido por ingredientes insuficientes', async () => {
  const fetchAnterior = globalThis.fetch
  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    text: async () => JSON.stringify({
      detail: 'Existencia insuficiente del ingrediente Tomate.',
    }),
  })
  try {
    await assert.rejects(
      api('pedidos', 'Basic prueba', { method: 'POST', body: '{}' }),
      /Existencia insuficiente del ingrediente Tomate/,
    )
  } finally {
    globalThis.fetch = fetchAnterior
  }
})

test('presenta los errores de validación sin mostrar JSON crudo', () => {
  assert.equal(
    mensajeErrorApi({ items: ['El pedido no puede estar vacío.'] }, 400),
    'items: El pedido no puede estar vacío.',
  )
  assert.equal(
    mensajeErrorApi({ detail: 'La sesión está cerrada.' }, 409),
    'La sesión está cerrada.',
  )
})

test('muestra un mensaje comprensible si Django no responde', async () => {
  const fetchAnterior = globalThis.fetch
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  try {
    await assert.rejects(api('me', 'Basic prueba'), /No se pudo conectar con el servidor/)
  } finally {
    globalThis.fetch = fetchAnterior
  }
})

test('las consultas GET de sincronización no usan una respuesta almacenada en navegador', async () => {
  const fetchAnterior = globalThis.fetch
  let opcionesRecibidas
  globalThis.fetch = async (_ruta, opciones) => {
    opcionesRecibidas = opciones
    return { ok: true, text: async () => '[]' }
  }
  try {
    await api('cocina/cola', 'Basic prueba')
    assert.equal(opcionesRecibidas.cache, 'no-store')
  } finally {
    globalThis.fetch = fetchAnterior
  }
})
