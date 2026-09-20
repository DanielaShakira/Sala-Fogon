const estados = Object.freeze({
  EN_COLA: 'EN COLA',
  EN_PREPARACION: 'EN PREPARACIÓN',
  LISTO: 'LISTO',
  CANCELADO: 'CANCELADO',
  EN_CURSO: 'EN CURSO',
  COMPLETO: 'COMPLETO',
})

const roles = Object.freeze({ ADMIN: 'Administrador', MESERO: 'Mesero', COCINERO: 'Cocinero' })

export function etiquetaEstado(codigo) {
  return estados[codigo] ?? (codigo || 'Sin ítems')
}

export function etiquetaRol(codigo) {
  return roles[codigo] ?? codigo
}
