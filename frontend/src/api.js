export async function api(ruta, autorizacion, opciones = {}) {
  const respuesta = await fetch(`/api/${ruta}/`, {
    ...opciones,
    headers: {
      Authorization: autorizacion,
      ...(opciones.body ? { 'Content-Type': 'application/json' } : {}),
    },
  })
  const datos = await respuesta.json()
  if (!respuesta.ok) {
    const detalle = datos.detail || JSON.stringify(datos)
    throw new Error(typeof detalle === 'string' ? detalle : JSON.stringify(detalle))
  }
  return datos
}
