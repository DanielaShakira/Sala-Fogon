import { useEffect, useRef, useState } from 'react'
import { createLatestRequestGuard } from './latestRequest.js'
import { api } from './api.js'
import Cuenta from './Cuenta.jsx'
import './App.css'

function basicHeader(usuario, clave) {
  const bytes = new TextEncoder().encode(`${usuario}:${clave}`)
  return `Basic ${btoa(Array.from(bytes, (byte) => String.fromCharCode(byte)).join(''))}`
}

const etiquetasPedido = {
  EN_COLA: 'En cola',
  EN_CURSO: 'En curso',
  COMPLETO: 'Completo',
  CANCELADO: 'Cancelado',
}

function Cocina({ autorizacion }) {
  const [cola, setCola] = useState([])
  const [ocupado, setOcupado] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  const colaGuard = useRef(null)
  if (colaGuard.current === null) colaGuard.current = createLatestRequestGuard()

  async function refrescar() {
    const sigueVigente = colaGuard.current.begin('cola')
    try {
      const datos = await api('cocina/cola', autorizacion)
      if (sigueVigente()) {
        setCola(datos)
        setError('')
      }
    } catch (fallo) {
      if (sigueVigente()) setError(fallo.message)
    }
  }

  useEffect(() => {
    colaGuard.current.select('cola')
    void refrescar()
    return () => colaGuard.current.select(null)
  }, [autorizacion])

  async function avanzar(itemId, accion) {
    colaGuard.current.invalidate()
    setOcupado(true)
    setError('')
    setMensaje('')
    let falloOperacion = null
    try {
      await api(`items/${itemId}/${accion}`, autorizacion, { method: 'POST' })
      setMensaje(accion === 'iniciar' ? 'Preparación iniciada.' : 'Plato marcado como listo.')
    } catch (fallo) {
      falloOperacion = fallo
    } finally {
      await refrescar()
      if (falloOperacion) setError(falloOperacion.message)
      setOcupado(false)
    }
  }

  return <section className="panel">
    <div className="cabecera"><h2>Cola de cocina</h2><button type="button" disabled={ocupado} onClick={refrescar}>Actualizar</button></div>
    {cola.length === 0 && <p>No hay ítems pendientes.</p>}
    {cola.map((pedido) => <article className="pedido" key={pedido.id}>
      <h3>Pedido {pedido.id} · Mesa {pedido.mesa_numero}</h3>
      <p>Estado general: <strong>{etiquetasPedido[pedido.estado_general] || 'Sin ítems'}</strong></p>
      <p>Creado: {new Date(pedido.fecha_hora_creacion).toLocaleString()}</p>
      {pedido.observaciones && <p>Observaciones: {pedido.observaciones}</p>}
      <ul className="lista-items">{pedido.items.map((item) => <li key={item.id}>
        <span>{item.plato} — {item.estado}</span>
        {item.estado === 'EN_COLA' && <button type="button" disabled={ocupado} onClick={() => avanzar(item.id, 'iniciar')}>Iniciar</button>}
        {item.estado === 'EN_PREPARACION' && <button type="button" disabled={ocupado} onClick={() => avanzar(item.id, 'listo')}>Marcar listo</button>}
      </li>)}</ul>
    </article>)}
    <div aria-live="polite">{mensaje && <p className="ok">{mensaje}</p>}{error && <p className="error">{error}</p>}</div>
  </section>
}

function App() {
  const [usuario, setUsuario] = useState('')
  const [clave, setClave] = useState('')
  const [autorizacion, setAutorizacion] = useState('')
  const [perfil, setPerfil] = useState(null)
  const [mesas, setMesas] = useState([])
  const [platos, setPlatos] = useState([])
  const [pedidosMesa, setPedidosMesa] = useState([])
  const [mesaId, setMesaId] = useState('')
  const [sesionId, setSesionId] = useState(null)
  const [borrador, setBorrador] = useState({})
  const [observaciones, setObservaciones] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [revisionCuenta, setRevisionCuenta] = useState(0)
  const pedidosGuard = useRef(null)
  if (pedidosGuard.current === null) pedidosGuard.current = createLatestRequestGuard()

  async function cargarPedidos(sesionObjetivo) {
    const sigueVigente = pedidosGuard.current.begin(sesionObjetivo)
    try {
      const datos = await api(`sesiones/${sesionObjetivo}/pedidos`, autorizacion)
      if (sigueVigente()) {
        setPedidosMesa(datos)
        setError('')
        return datos
      }
    } catch (fallo) {
      if (sigueVigente()) setError(fallo.message)
    }
    return null
  }

  async function ingresar(evento) {
    evento.preventDefault()
    setOcupado(true)
    setError('')
    try {
      const encabezado = basicHeader(usuario, clave)
      const datosPerfil = await api('me', encabezado)
      if (datosPerfil.rol === 'MESERO') {
        const [datosMesas, datosPlatos] = await Promise.all([
          api('mesas', encabezado), api('platos', encabezado),
        ])
        setMesas(datosMesas)
        setPlatos(datosPlatos)
      } else if (datosPerfil.rol !== 'COCINERO') {
        throw new Error('Esta interfaz requiere el rol MESERO o COCINERO.')
      }
      setAutorizacion(encabezado)
      setPerfil(datosPerfil)
      setClave('')
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  function salir() {
    pedidosGuard.current.select(null)
    setAutorizacion('')
    setPerfil(null)
    setMesaId('')
    setSesionId(null)
    setBorrador({})
    setPedidosMesa([])
    setObservaciones('')
    setMensaje('')
    setError('')
  }

  function seleccionarMesa(valor) {
    setMesaId(valor)
    const mesa = mesas.find((candidata) => candidata.id === Number(valor))
    const sesionNueva = mesa?.sesion_propia ? mesa.sesion_activa_id : null
    pedidosGuard.current.select(sesionNueva)
    setSesionId(sesionNueva)
    setPedidosMesa([])
    setBorrador({})
    setMensaje('')
    setError('')
    if (sesionNueva !== null) void cargarPedidos(sesionNueva)
  }

  async function abrirSesion() {
    setOcupado(true)
    setError('')
    try {
      const sesion = await api('sesiones', autorizacion, {
        method: 'POST', body: JSON.stringify({ mesa_id: Number(mesaId) }),
      })
      pedidosGuard.current.select(sesion.id)
      setSesionId(sesion.id)
      setPedidosMesa([])
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
    const sesionObjetivo = pedidosGuard.current.current()
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
        body: JSON.stringify({ sesion_id: sesionObjetivo, observaciones, items }),
      })
      setBorrador({})
      setObservaciones('')
      setRevisionCuenta((actual) => actual + 1)
      setMensaje(`Pedido enviado a cocina: ${pedido.items.length} unidad(es) en cola. ID global ${pedido.id}.`)
      const pedidosActualizados = await cargarPedidos(sesionObjetivo)
      const numeroLocal = pedidosActualizados?.find((actual) => actual.id === pedido.id)?.numero_en_sesion
      if (numeroLocal) {
        setMensaje(`Pedido ${numeroLocal} enviado a cocina: ${pedido.items.length} unidad(es) en cola. ID global ${pedido.id}.`)
      }
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

  async function actualizarPedidos() {
    const sesionObjetivo = pedidosGuard.current.current()
    if (sesionObjetivo === null) return
    setOcupado(true)
    await cargarPedidos(sesionObjetivo)
    setOcupado(false)
  }

  async function cancelarItem(itemId, sesionDeLaLista) {
    if (pedidosGuard.current.current() !== sesionDeLaLista ||
        !pedidosMesa.some((pedido) => pedido.items.some((item) => item.id === itemId && item.estado === 'EN_COLA' && !item.pagado))) {
      return
    }
    pedidosGuard.current.invalidate()
    setOcupado(true)
    setError('')
    setMensaje('')
    let falloOperacion = null
    try {
      await api(`items/${itemId}/cancelar`, autorizacion, { method: 'POST' })
      setMensaje('Plato cancelado; ingredientes devueltos.')
      if (pedidosGuard.current.current() === sesionDeLaLista) setRevisionCuenta((actual) => actual + 1)
    } catch (fallo) {
      falloOperacion = fallo
    } finally {
      if (pedidosGuard.current.current() === sesionDeLaLista) {
        await cargarPedidos(sesionDeLaLista)
        try {
          setPlatos(await api('platos', autorizacion))
        } catch (fallo) {
          setError(`No se pudo actualizar el catálogo: ${fallo.message}`)
        }
        if (falloOperacion) setError(falloOperacion.message)
      }
      setOcupado(false)
    }
  }

  async function sesionCerrada(sesionCerradaId) {
    if (pedidosGuard.current.current() !== sesionCerradaId) return
    pedidosGuard.current.select(null)
    setSesionId(null)
    setPedidosMesa([])
    setBorrador({})
    setObservaciones('')
    setMensaje(`Sesión ${sesionCerradaId} cerrada. La mesa puede iniciar una nueva atención.`)
    try {
      setMesas(await api('mesas', autorizacion))
    } catch (fallo) {
      setError(`La sesión se cerró, pero no se pudo actualizar la lista de mesas: ${fallo.message}`)
    }
  }

  const mesaSeleccionada = mesas.find((mesa) => mesa.id === Number(mesaId))
  const totalUnidades = Object.values(borrador).reduce((total, cantidad) => total + cantidad, 0)

  return (
    <main className="page">
      <h1>Sala Fogón</h1>
      <p>Sesiones de mesa, pedidos y cocina</p>
      {!perfil ? (
        <form className="panel" onSubmit={ingresar}>
          <h2>Acceso del personal</h2>
          <label>Usuario <input autoComplete="username" value={usuario} onChange={(e) => setUsuario(e.target.value)} required /></label>
          <label>Contraseña <input type="password" autoComplete="current-password" value={clave} onChange={(e) => setClave(e.target.value)} required /></label>
          <button disabled={ocupado}>Ingresar</button>
          <p className="nota">Las credenciales se mantienen solo en esta pestaña durante la sesión.</p>
        </form>
      ) : (
        <>
          <div className="cabecera"><strong>{perfil.rol === 'COCINERO' ? 'Cocinero' : 'Mesero'}: {perfil.nombre}</strong><button type="button" disabled={ocupado} onClick={salir}>Salir</button></div>
          {perfil.rol === 'COCINERO' ? <Cocina autorizacion={autorizacion} /> : <>
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
            <section className="panel">
              <div className="cabecera"><h2>Pedidos de esta sesión</h2><button type="button" disabled={ocupado} onClick={actualizarPedidos}>Actualizar</button></div>
              {pedidosMesa.length === 0 && <p>Aún no hay pedidos en esta sesión.</p>}
              {pedidosMesa.map((pedido) => <article className="pedido" key={pedido.id}>
                <div className="cabecera pedido-cabecera"><h3>Pedido {pedido.numero_en_sesion}</h3><small>ID global {pedido.id}</small></div>
                <p>Estado general: <strong>{etiquetasPedido[pedido.estado_general] || 'Sin ítems'}</strong></p>
                <ul className="lista-items">{pedido.items.map((item) => <li key={item.id}>
                  <span>{item.plato} — {item.estado}</span>
                  {item.estado === 'EN_COLA' && !item.pagado && <button type="button" disabled={ocupado} onClick={() => cancelarItem(item.id, sesionId)}>Cancelar</button>}
                </li>)}</ul>
              </article>)}
            </section>
            <Cuenta key={sesionId} sesionId={sesionId} autorizacion={autorizacion} revision={revisionCuenta} alCerrar={sesionCerrada} />
          </>}
          </>}
        </>
      )}
      <div aria-live="polite">{mensaje && <p className="ok">{mensaje}</p>}{error && <p className="error">{error}</p>}</div>
    </main>
  )
}

export default App
