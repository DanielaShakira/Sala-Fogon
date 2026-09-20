function textosError(valor, campo = '') {
  if (typeof valor === 'string') return [campo ? `${campo}: ${valor}` : valor]
  if (Array.isArray(valor)) return valor.flatMap((parte) => textosError(parte, campo))
  if (valor && typeof valor === 'object') {
    return Object.entries(valor).flatMap(([clave, parte]) =>
      textosError(parte, clave === 'detail' || clave === 'non_field_errors'
        ? campo : [campo, clave.replaceAll('_', ' ')].filter(Boolean).join(' · ')))
  }
  return []
}

export function mensajeErrorApi(datos, estado) {
  const textos = textosError(datos)
  return textos.length ? textos.join(' ') : `La operación no pudo completarse (HTTP ${estado}).`
}

export async function api(ruta, autorizacion, opciones = {}) {
  let respuesta
  try {
    respuesta = await fetch(`/api/${ruta}/`, {
      cache: (opciones.method ?? 'GET').toUpperCase() === 'GET' ? 'no-store' : 'default',
      ...opciones,
      headers: {
        Authorization: autorizacion,
        ...(opciones.body ? { 'Content-Type': 'application/json' } : {}),
      },
    })
  } catch {
    throw new Error('No se pudo conectar con el servidor. Comprueba que Django esté en ejecución.')
  }
  const contenido = await respuesta.text()
  let datos
  try {
    datos = contenido ? JSON.parse(contenido) : null
  } catch {
    if (!respuesta.ok) throw new Error(`La operación no pudo completarse (HTTP ${respuesta.status}).`)
    throw new Error('El servidor devolvió una respuesta no válida.')
  }
  if (!respuesta.ok) throw new Error(mensajeErrorApi(datos, respuesta.status))
  return datos
}
