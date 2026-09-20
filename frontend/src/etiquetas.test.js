import assert from 'node:assert/strict'
import test from 'node:test'
import { etiquetaEstado, etiquetaRol } from './etiquetas.js'

test('item and order states have readable labels without changing their codes', () => {
  const esperados = {
    EN_COLA: 'EN COLA', EN_PREPARACION: 'EN PREPARACIÓN',
    LISTO: 'LISTO', CANCELADO: 'CANCELADO',
    EN_CURSO: 'EN CURSO', COMPLETO: 'COMPLETO',
  }
  for (const [codigo, etiqueta] of Object.entries(esperados)) {
    const item = { estado: codigo }
    assert.equal(etiquetaEstado(item.estado), etiqueta)
    assert.equal(item.estado, codigo)
  }
  assert.equal(etiquetaEstado(null), 'Sin ítems')
})

test('employee roles are displayed as names while keeping API values intact', () => {
  assert.equal(etiquetaRol('MESERO'), 'Mesero')
  assert.equal(etiquetaRol('COCINERO'), 'Cocinero')
  assert.equal(etiquetaRol('ADMIN'), 'Administrador')
})
