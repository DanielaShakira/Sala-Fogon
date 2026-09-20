// The first successful read is a baseline. Only observed transitions to LISTO
// produce notices; revisiting a view or polling an unchanged item does not.
export function createReadyTracker() {
  let previous = null

  return {
    observe(pedidos) {
      const current = new Map()
      const ready = []
      for (const pedido of pedidos) {
        for (const item of pedido.items) {
          current.set(item.id, item.estado)
          if (previous !== null &&
              ['EN_COLA', 'EN_PREPARACION'].includes(previous.get(item.id)) &&
              item.estado === 'LISTO') {
            ready.push({
              id: item.id,
              plato: item.plato,
              mesa: pedido.mesa_numero,
              pedido: pedido.numero_en_sesion,
            })
          }
        }
      }
      previous = current
      return ready
    },
    reset() { previous = null },
  }
}

export function mensajeItemsListos(items) {
  const grupos = new Map()
  for (const item of items) {
    const clave = `${item.mesa}:${item.pedido}:${item.plato}`
    const grupo = grupos.get(clave)
    if (grupo) grupo.cantidad += 1
    else grupos.set(clave, { ...item, cantidad: 1 })
  }
  const detalles = [...grupos.values()].map(({ plato, mesa, pedido, cantidad }) =>
    `${plato}${cantidad > 1 ? ` ×${cantidad}` : ''} (mesa ${mesa}, pedido ${pedido})`)
  return `${items.length === 1 ? 'Plato listo' : `${items.length} platos listos`}: ${detalles.join('; ')}.`
}
