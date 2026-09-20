import test from 'node:test'
import assert from 'node:assert/strict'
import { createAutoRefresh, createSingleFlight } from './autoRefresh.js'

function entornoPrueba() {
  const ventana = new EventTarget()
  const documento = new EventTarget()
  documento.hidden = false
  const pendientes = new Map()
  let siguienteId = 0
  const temporizadores = {
    setTimeout(fn) {
      const id = ++siguienteId
      pendientes.set(id, fn)
      return id
    },
    clearTimeout(id) { pendientes.delete(id) },
  }
  return {
    ventana, documento, temporizadores, pendientes,
    conectado: () => true,
    async siguiente() {
      const [id, fn] = pendientes.entries().next().value
      pendientes.delete(id)
      await fn()
    },
  }
}

test('dos clientes independientes reciben nuevos pedidos y sus cambios de estado', async () => {
  const entorno = entornoPrueba()
  const pedidos = []
  let vistaMesero = []
  let vistaCocina = []
  const mesero = createAutoRefresh(
    async () => { vistaMesero = pedidos.map((pedido) => ({ ...pedido })) }, 3000, entorno,
  )
  const cocina = createAutoRefresh(
    async () => { vistaCocina = pedidos.map((pedido) => ({ ...pedido })) }, 3000, entorno,
  )
  mesero.start()
  cocina.start()
  assert.equal(entorno.pendientes.size, 2)
  pedidos.push({ id: 1, estado: 'EN_COLA' })
  await entorno.siguiente()
  await entorno.siguiente()
  assert.deepEqual(vistaMesero, [{ id: 1, estado: 'EN_COLA' }])
  assert.deepEqual(vistaCocina, vistaMesero)
  pedidos[0].estado = 'EN_PREPARACION'
  await entorno.siguiente()
  await entorno.siguiente()
  assert.equal(vistaMesero[0].estado, 'EN_PREPARACION')
  assert.equal(vistaCocina[0].estado, 'EN_PREPARACION')
  mesero.stop()
  cocina.stop()
  assert.equal(entorno.pendientes.size, 0)
})

test('no superpone consultas y reanuda al volver a una pestaña visible', async () => {
  const entorno = entornoPrueba()
  let terminar
  let llamadas = 0
  const control = createAutoRefresh(() => {
    llamadas += 1
    return new Promise((resolver) => { terminar = resolver })
  }, 3000, entorno)
  control.start()
  const consulta = entorno.siguiente()
  assert.equal(llamadas, 1)
  entorno.ventana.dispatchEvent(new Event('focus'))
  assert.equal(llamadas, 1)
  terminar()
  await consulta
  assert.equal(entorno.pendientes.size, 1)
  entorno.documento.hidden = true
  entorno.documento.dispatchEvent(new Event('visibilitychange'))
  assert.equal(entorno.pendientes.size, 0)
  entorno.documento.hidden = false
  entorno.documento.dispatchEvent(new Event('visibilitychange'))
  assert.equal(llamadas, 2)
  terminar()
  await Promise.resolve()
  control.stop()
  assert.equal(entorno.pendientes.size, 0)
  entorno.ventana.dispatchEvent(new Event('focus'))
  assert.equal(llamadas, 2)
})

test('una falla temporal no detiene las actualizaciones posteriores', async () => {
  const entorno = entornoPrueba()
  let llamadas = 0
  const control = createAutoRefresh(async () => {
    llamadas += 1
    if (llamadas === 1) throw new Error('Red temporalmente no disponible')
  }, 3000, entorno)
  control.start()
  await entorno.siguiente()
  assert.equal(entorno.pendientes.size, 1)
  await entorno.siguiente()
  assert.equal(llamadas, 2)
  control.stop()
})

test('detiene consultas sin conexión y refresca al reconectar', async () => {
  const entorno = entornoPrueba()
  let hayConexion = true
  entorno.conectado = () => hayConexion
  let llamadas = 0
  const control = createAutoRefresh(async () => { llamadas += 1 }, 3000, entorno)
  control.start()
  hayConexion = false
  entorno.ventana.dispatchEvent(new Event('offline'))
  assert.equal(entorno.pendientes.size, 0)
  hayConexion = true
  entorno.ventana.dispatchEvent(new Event('online'))
  await Promise.resolve()
  assert.equal(llamadas, 1)
  assert.equal(entorno.pendientes.size, 1)
  control.stop()
})

test('comparte lecturas simultáneas y permite forzar otra tras una escritura', async () => {
  const consulta = createSingleFlight()
  const resolutores = []
  let llamadas = 0
  const trabajo = () => {
    llamadas += 1
    return new Promise((resolver) => resolutores.push(resolver))
  }
  const primera = consulta.run('pedidos', trabajo)
  const compartida = consulta.run('pedidos', trabajo)
  assert.equal(primera, compartida)
  assert.equal(llamadas, 1)
  const nueva = consulta.run('pedidos', trabajo, { force: true })
  assert.equal(llamadas, 2)
  resolutores[1]('nuevo')
  assert.equal(await nueva, 'nuevo')
  resolutores[0]('anterior')
  assert.equal(await primera, 'anterior')
})
