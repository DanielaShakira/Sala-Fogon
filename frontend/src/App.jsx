import { useState } from 'react'
import './App.css'

function basicHeader(usuario, clave) {
  const bytes = new TextEncoder().encode(`${usuario}:${clave}`)
  return `Basic ${btoa(Array.from(bytes, (byte) => String.fromCharCode(byte)).join(''))}`
}

async function api(ruta, autorizacion, opciones = {}) {
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

function App() {
  const [usuario, setUsuario] = useState('')
  const [clave, setClave] = useState('')
  const [autorizacion, setAutorizacion] = useState('')
  const [perfil, setPerfil] = useState(null)
  const [mesas, setMesas] = useState([])
  const [platos, setPlatos] = useState([])
  const [mesaId, setMesaId] = useState('')
  const [sesionId, setSesionId] = useState(null)
  const [borrador, setBorrador] = useState({})
  const [observaciones, setObservaciones] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)

  async function ingresar(evento) {
    evento.preventDefault()
    setOcupado(true)
    setError('')
    try {
      const encabezado = basicHeader(usuario, clave)
      const datosPerfil = await api('me', encabezado)
      const [datosMesas, datosPlatos] = await Promise.all([
        api('mesas', encabezado), api('platos', encabezado),
      ])
      setAutorizacion(encabezado)
      setPerfil(datosPerfil)
      setMesas(datosMesas)
      setPlatos(datosPlatos)
      setClave('')
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  function salir() {
    setAutorizacion('')
    setPerfil(null)
    setMesaId('')
    setSesionId(null)
    setBorrador({})
    setObservaciones('')
    setMensaje('')
    setError('')
  }

  function seleccionarMesa(valor) {
    setMesaId(valor)
    const mesa = mesas.find((candidata) => candidata.id === Number(valor))
    setSesionId(mesa?.sesion_propia ? mesa.sesion_activa_id : null)
    setBorrador({})
    setMensaje('')
    setError('')
  }

  async function abrirSesion() {
    setOcupado(true)
    setError('')
    try {
      const sesion = await api('sesiones', autorizacion, {
        method: 'POST', body: JSON.stringify({ mesa_id: Number(mesaId) }),
      })
      setSesionId(sesion.id)
      setMensaje(`Sesión ${sesion.id} abierta para la mesa seleccionada.`)
      try {
        setMesas(await api('mesas', autorizacion))
      } catch (fallo) {
        setError(`La sesión se abrió, pero no se pudo actualizar la lista de mesas: ${fallo.message}`)
      }
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  function cambiarCantidad(platoId, diferencia) {
    setBorrador((actual) => {
      const cantidad = Math.max(0, (actual[platoId] || 0) + diferencia)
      const siguiente = { ...actual }
      if (cantidad) siguiente[platoId] = cantidad
      else delete siguiente[platoId]
      return siguiente
    })
  }

  async function enviarPedido() {
    const items = Object.entries(borrador).map(([platoId, cantidad]) => ({
      plato_id: Number(platoId), cantidad,
    }))
    if (!items.length) {
      setError('Añade al menos una unidad al pedido.')
      return
    }
    setOcupado(true)
    setError('')
    try {
      const pedido = await api('pedidos', autorizacion, {
        method: 'POST',
        body: JSON.stringify({ sesion_id: sesionId, observaciones, items }),
      })
      setBorrador({})
      setObservaciones('')
      setMensaje(`Pedido ${pedido.id} enviado a cocina: ${pedido.items.length} unidad(es) en cola.`)
      try {
        setPlatos(await api('platos', autorizacion))
      } catch (fallo) {
        setError(`El pedido se envió, pero no se pudo actualizar el catálogo: ${fallo.message}`)
      }
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  const mesaSeleccionada = mesas.find((mesa) => mesa.id === Number(mesaId))
  const totalUnidades = Object.values(borrador).reduce((total, cantidad) => total + cantidad, 0)

  return (
    <main className="page">
      <h1>Sala Fogón</h1>
      <p>Sesiones de mesa y envío de pedidos a cocina</p>
      {!perfil ? (
        <form className="panel" onSubmit={ingresar}>
          <h2>Acceso de mesero</h2>
          <label>Usuario <input autoComplete="username" value={usuario} onChange={(e) => setUsuario(e.target.value)} required /></label>
          <label>Contraseña <input type="password" autoComplete="current-password" value={clave} onChange={(e) => setClave(e.target.value)} required /></label>
          <button disabled={ocupado}>Ingresar</button>
          <p className="nota">Las credenciales se mantienen solo en esta pestaña durante la sesión.</p>
        </form>
      ) : (
        <>
          <div className="cabecera"><strong>Mesero: {perfil.nombre}</strong><button type="button" disabled={ocupado} onClick={salir}>Salir</button></div>
          <section className="panel">
            <h2>Mesa</h2>
            <label>Seleccionar mesa
              <select value={mesaId} disabled={ocupado} onChange={(e) => seleccionarMesa(e.target.value)}>
                <option value="">Elige una mesa</option>
                {mesas.map((mesa) => <option key={mesa.id} value={mesa.id}>Mesa {mesa.numero}{mesa.sesion_activa_id ? mesa.sesion_propia ? ' — sesión propia' : ' — ocupada' : ''}</option>)}
              </select>
            </label>
            {mesaSeleccionada && !mesaSeleccionada.sesion_activa_id && <button type="button" disabled={ocupado} onClick={abrirSesion}>Abrir sesión</button>}
            {mesaSeleccionada?.sesion_activa_id && !mesaSeleccionada.sesion_propia && <p>Esta mesa ya tiene una sesión activa.</p>}
            {sesionId && <p>Sesión activa: <strong>{sesionId}</strong></p>}
          </section>
          {sesionId && <>
            <section className="panel">
              <h2>Platos</h2>
              {platos.length === 0 && <p>No hay platos registrados.</p>}
              <ul className="platos">
                {platos.map((plato) => <li key={plato.id}>
                  <div><strong>{plato.nombre}</strong><span> — ${plato.precio}</span><br /><small>{plato.disponible ? 'Disponible' : 'No disponible'}</small></div>
                  <div className="controles">
                    <button type="button" aria-label={`Quitar ${plato.nombre}`} disabled={ocupado || !borrador[plato.id]} onClick={() => cambiarCantidad(plato.id, -1)}>−</button>
                    <output>{borrador[plato.id] || 0}</output>
                    <button type="button" aria-label={`Añadir ${plato.nombre}`} disabled={ocupado || !plato.disponible} onClick={() => cambiarCantidad(plato.id, 1)}>+</button>
                  </div>
                </li>)}
              </ul>
            </section>
            <section className="panel">
              <h2>Pedido temporal</h2>
              <p>{totalUnidades} unidad(es). Se guardará al confirmar el envío.</p>
              <label>Observaciones <textarea value={observaciones} onChange={(e) => setObservaciones(e.target.value)} /></label>
              <button type="button" disabled={ocupado || totalUnidades === 0} onClick={enviarPedido}>Enviar a cocina</button>
            </section>
          </>}
        </>
      )}
      <div aria-live="polite">{mensaje && <p className="ok">{mensaje}</p>}{error && <p className="error">{error}</p>}</div>
    </main>
  )
}

export default App
