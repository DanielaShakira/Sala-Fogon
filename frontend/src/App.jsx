import { useCallback, useEffect, useRef, useState } from 'react'
import { createLatestRequestGuard } from './latestRequest.js'
import { createSingleFlight, INTERVALO_CONFIGURACION, INTERVALO_OPERATIVO, useAutoRefresh } from './autoRefresh.js'
import { api } from './api.js'
import Cuenta from './Cuenta.jsx'
import Administracion from './Administracion.jsx'
import { etiquetaEstado } from './etiquetas.js'
import { createReadyTracker, mensajeItemsListos } from './readyNotifications.js'
import { formatPrice } from './money.js'
import AvisoGlobal from './AvisoGlobal.jsx'
import './App.css'

function basicHeader(usuario, clave) {
  const bytes = new TextEncoder().encode(`${usuario}:${clave}`)
  return `Basic ${btoa(Array.from(bytes, (byte) => String.fromCharCode(byte)).join(''))}`
}

function Cocina({ autorizacion, avisar }) {
  const [cola, setCola] = useState([])
  const [ocupado, setOcupado] = useState(false)
  const [errorSincronizacion, setErrorSincronizacion] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  const colaGuard = useRef(null)
  if (colaGuard.current === null) colaGuard.current = createLatestRequestGuard()
  const colaFlight = useRef(null)
  if (colaFlight.current === null) colaFlight.current = createSingleFlight()
  function reportarError(texto) { setError(texto); avisar('error', texto) }
  function reportarExito(texto) { setMensaje(texto); avisar('exito', texto) }

  function refrescar({ silencioso = false, force = false } = {}) {
    return colaFlight.current.run(autorizacion, async () => {
      const sigueVigente = colaGuard.current.begin('cola')
      try {
        const datos = await api('cocina/cola', autorizacion)
        if (sigueVigente()) {
          setCola(datos)
          setErrorSincronizacion(false)
          if (!silencioso) setError('')
        }
      } catch (fallo) {
        if (sigueVigente()) {
          if (silencioso) setErrorSincronizacion(true)
          else reportarError(fallo.message)
        }
      }
    }, { force })
  }

  useAutoRefresh(() => refrescar({ silencioso: true }), INTERVALO_OPERATIVO, !ocupado)

  useEffect(() => {
    colaGuard.current.select('cola')
    void refrescar({ force: true })
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
      reportarExito(accion === 'iniciar' ? 'Preparación iniciada.' : 'Plato marcado como listo.')
    } catch (fallo) {
      falloOperacion = fallo
    } finally {
      await refrescar({ force: true })
      if (falloOperacion) reportarError(falloOperacion.message)
      setOcupado(false)
    }
  }

  return <section className="workspace-section">
    <div className="section-heading"><div><span className="eyebrow">Preparación</span><h2>Cola de cocina</h2><p>Pedidos pendientes, del más antiguo al más reciente.</p></div></div>
    {errorSincronizacion && <p className="nota" role="status">No se pudo actualizar la cola. Se reintentará automáticamente.</p>}
    {cola.length === 0 && <div className="empty-state"><strong>La cola está al día</strong><p>No hay ítems pendientes de preparación.</p></div>}
    <div className="order-grid">{cola.map((pedido) => <article className="order-card" key={pedido.id}>
      <div className="order-card-header"><div><span className="eyebrow">Mesa {pedido.mesa_numero}</span><h3>Pedido #{pedido.id}</h3></div><span className="estado" data-estado={pedido.estado_general}>{etiquetaEstado(pedido.estado_general)}</span></div>
      <p className="order-meta">Recibido {new Date(pedido.fecha_hora_creacion).toLocaleString()}</p>
      {pedido.observaciones && <p className="order-note"><strong>Observaciones</strong><br />{pedido.observaciones}</p>}
      <ul className="item-list">{pedido.items.map((item) => <li key={item.id}>
        <div className="item-main"><strong>{item.plato}</strong><span className="estado" data-estado={item.estado}>{etiquetaEstado(item.estado)}</span></div>
        {item.estado === 'EN_COLA' && <button className="button button-primary" type="button" disabled={ocupado} onClick={() => avanzar(item.id, 'iniciar')}>Iniciar preparación</button>}
        {item.estado === 'EN_PREPARACION' && <button className="button button-primary" type="button" disabled={ocupado} onClick={() => avanzar(item.id, 'listo')}>Marcar listo</button>}
      </li>)}</ul>
    </article>)}</div>
    <div>{mensaje && <p className="ok">{mensaje}</p>}{error && <p className="error">{error}</p>}</div>
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
  const [avisos, setAvisos] = useState([])
  const [ocupado, setOcupado] = useState(false)
  const [errorSincronizacion, setErrorSincronizacion] = useState({ pedidos: false, platos: false, mesas: false })
  const [revisionCuenta, setRevisionCuenta] = useState(0)
  const pedidosGuard = useRef(null)
  if (pedidosGuard.current === null) pedidosGuard.current = createLatestRequestGuard()
  const seguimientoGuard = useRef(null)
  if (seguimientoGuard.current === null) seguimientoGuard.current = createLatestRequestGuard()
  const listos = useRef(null)
  if (listos.current === null) listos.current = createReadyTracker()
  const platosGuard = useRef(null)
  if (platosGuard.current === null) platosGuard.current = createLatestRequestGuard()
  const mesasGuard = useRef(null)
  if (mesasGuard.current === null) mesasGuard.current = createLatestRequestGuard()
  const pedidosFlight = useRef(null)
  if (pedidosFlight.current === null) pedidosFlight.current = createSingleFlight()
  const platosFlight = useRef(null)
  if (platosFlight.current === null) platosFlight.current = createSingleFlight()
  const mesasFlight = useRef(null)
  if (mesasFlight.current === null) mesasFlight.current = createSingleFlight()
  const avisar = useCallback((tipo, texto) => setAvisos((actual) => tipo === 'listo'
    ? [...actual, { tipo, texto }]
    : [{ tipo, texto }, ...actual.filter((pendiente) => pendiente.tipo === 'listo')]), [])
  const cerrarAviso = useCallback(() => setAvisos((actual) => actual.slice(1)), [])
  function reportarError(texto) { setError(texto); avisar('error', texto) }
  function reportarExito(texto) { setMensaje(texto); avisar('exito', texto) }

  function estadoSincronizacion(recurso, error) {
    setErrorSincronizacion((actual) => actual[recurso] === error
      ? actual : { ...actual, [recurso]: error })
  }

  function cargarPedidos(sesionObjetivo, { silencioso = false, force = false } = {}) {
    return pedidosFlight.current.run(autorizacion, async () => {
      const sigueVigente = seguimientoGuard.current.begin(autorizacion)
      try {
        const datos = await api('mis-pedidos-activos', autorizacion)
        if (sigueVigente()) {
          const nuevosListos = listos.current.observe(datos)
          setPedidosMesa(datos.filter((pedido) => pedido.sesion_id === pedidosGuard.current.current()))
          estadoSincronizacion('pedidos', false)
          if (!silencioso) setError('')
          if (nuevosListos.length) avisar('listo', mensajeItemsListos(nuevosListos))
          return datos.filter((pedido) => pedido.sesion_id === sesionObjetivo)
        }
      } catch (fallo) {
        if (sigueVigente()) {
          if (silencioso) estadoSincronizacion('pedidos', true)
          else reportarError(fallo.message)
        }
      }
      return null
    }, { force })
  }

  function cargarPlatos({ silencioso = false, force = false } = {}) {
    return platosFlight.current.run(autorizacion, async () => {
      const sigueVigente = platosGuard.current.begin(autorizacion)
      try {
        const datos = await api('platos', autorizacion)
        if (sigueVigente()) {
          setPlatos(datos)
          estadoSincronizacion('platos', false)
        }
        return datos
      } catch (fallo) {
        if (sigueVigente()) {
          if (silencioso) estadoSincronizacion('platos', true)
          else throw fallo
        }
        return null
      }
    }, { force })
  }

  function cargarMesas({ silencioso = false, force = false } = {}) {
    return mesasFlight.current.run(autorizacion, async () => {
      const sigueVigente = mesasGuard.current.begin(autorizacion)
      try {
        const datos = await api('mesas', autorizacion)
        if (sigueVigente()) {
          setMesas(datos)
          estadoSincronizacion('mesas', false)
        }
        return datos
      } catch (fallo) {
        if (sigueVigente()) {
          if (silencioso) estadoSincronizacion('mesas', true)
          else throw fallo
        }
        return null
      }
    }, { force })
  }

  useEffect(() => {
    platosGuard.current.select(autorizacion)
    mesasGuard.current.select(autorizacion)
  }, [autorizacion])

  useAutoRefresh(
    () => cargarPedidos(pedidosGuard.current.current(), { silencioso: true }),
    INTERVALO_OPERATIVO,
    perfil?.rol === 'MESERO' && !ocupado,
  )
  useAutoRefresh(
    () => Promise.all([
      cargarMesas({ silencioso: true }),
      cargarPlatos({ silencioso: true }),
    ]),
    INTERVALO_CONFIGURACION,
    perfil?.rol === 'MESERO' && !ocupado,
  )

  useEffect(() => {
    if (perfil?.rol !== 'MESERO') return undefined
    seguimientoGuard.current.select(autorizacion)
    void cargarPedidos(null, { silencioso: true, force: true })
    return () => seguimientoGuard.current.select(null)
  }, [autorizacion, perfil?.rol])

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
      } else if (datosPerfil.rol !== 'COCINERO' && datosPerfil.rol !== 'ADMIN') {
        throw new Error('Esta cuenta no tiene un rol disponible en la interfaz.')
      }
      setAutorizacion(encabezado)
      setPerfil(datosPerfil)
      listos.current.reset()
      setClave('')
    } catch (fallo) {
      reportarError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  function salir() {
    pedidosGuard.current.select(null)
    seguimientoGuard.current.select(null)
    listos.current.reset()
    platosGuard.current.select(null)
    mesasGuard.current.select(null)
    setAutorizacion('')
    setPerfil(null)
    setMesaId('')
    setSesionId(null)
    setBorrador({})
    setPedidosMesa([])
    setObservaciones('')
    setMensaje('')
    setError('')
    setAvisos([])
    setErrorSincronizacion({ pedidos: false, platos: false, mesas: false })
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
    if (sesionNueva !== null) void cargarPedidos(sesionNueva, { force: true })
  }

  async function abrirSesion() {
    mesasGuard.current.invalidate()
    setOcupado(true)
    setError('')
    try {
      const sesion = await api('sesiones', autorizacion, {
        method: 'POST', body: JSON.stringify({ mesa_id: Number(mesaId) }),
      })
      pedidosGuard.current.select(sesion.id)
      setSesionId(sesion.id)
      setPedidosMesa([])
      reportarExito(`Sesión ${sesion.id} abierta para la mesa seleccionada.`)
      try {
        await cargarMesas({ force: true })
      } catch (fallo) {
        reportarError(`La sesión se abrió, pero no se pudo actualizar la lista de mesas: ${fallo.message}`)
      }
    } catch (fallo) {
      reportarError(fallo.message)
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
      reportarError('Añade al menos una unidad al pedido.')
      return
    }
    pedidosGuard.current.invalidate()
    seguimientoGuard.current.invalidate()
    platosGuard.current.invalidate()
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
      reportarExito(`Pedido enviado a cocina: ${pedido.items.length} unidad(es) en cola. ID global ${pedido.id}.`)
      const pedidosActualizados = await cargarPedidos(sesionObjetivo, { force: true })
      const numeroLocal = pedidosActualizados?.find((actual) => actual.id === pedido.id)?.numero_en_sesion
      if (numeroLocal) {
        reportarExito(`Pedido ${numeroLocal} enviado a cocina: ${pedido.items.length} unidad(es) en cola. ID global ${pedido.id}.`)
      }
      try {
        await cargarPlatos({ force: true })
      } catch (fallo) {
        reportarError(`El pedido se envió, pero no se pudo actualizar el catálogo: ${fallo.message}`)
      }
    } catch (fallo) {
      reportarError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  async function cancelarItem(itemId, sesionDeLaLista) {
    if (pedidosGuard.current.current() !== sesionDeLaLista ||
        !pedidosMesa.some((pedido) => pedido.items.some((item) => item.id === itemId && item.estado === 'EN_COLA' && !item.pagado))) {
      return
    }
    pedidosGuard.current.invalidate()
    seguimientoGuard.current.invalidate()
    platosGuard.current.invalidate()
    setOcupado(true)
    setError('')
    setMensaje('')
    let falloOperacion = null
    try {
      await api(`items/${itemId}/cancelar`, autorizacion, { method: 'POST' })
      reportarExito('Plato cancelado; ingredientes devueltos.')
      if (pedidosGuard.current.current() === sesionDeLaLista) setRevisionCuenta((actual) => actual + 1)
    } catch (fallo) {
      falloOperacion = fallo
    } finally {
      if (pedidosGuard.current.current() === sesionDeLaLista) {
        await cargarPedidos(sesionDeLaLista, { force: true })
        try {
          await cargarPlatos({ force: true })
        } catch (fallo) {
          reportarError(`No se pudo actualizar el catálogo: ${fallo.message}`)
        }
        if (falloOperacion) reportarError(falloOperacion.message)
      }
      setOcupado(false)
    }
  }

  async function sesionCerrada(sesionCerradaId) {
    if (pedidosGuard.current.current() !== sesionCerradaId) return
    pedidosGuard.current.select(null)
    seguimientoGuard.current.invalidate()
    mesasGuard.current.invalidate()
    setSesionId(null)
    setPedidosMesa([])
    setBorrador({})
    setObservaciones('')
    reportarExito(`Sesión ${sesionCerradaId} cerrada. La mesa puede iniciar una nueva atención.`)
    try {
      await cargarMesas({ force: true })
    } catch (fallo) {
      reportarError(`La sesión se cerró, pero no se pudo actualizar la lista de mesas: ${fallo.message}`)
    }
  }

  const mesaSeleccionada = mesas.find((mesa) => mesa.id === Number(mesaId))
  const totalUnidades = Object.values(borrador).reduce((total, cantidad) => total + cantidad, 0)
  const lineasBorrador = platos.filter((plato) => borrador[plato.id])

  return (
    <div className="app-shell">
      <AvisoGlobal aviso={avisos[0]} alCerrar={cerrarAviso} />
      <header className="site-header"><div className="site-header-inner">
        <div className="brand"><span className="brand-mark" aria-hidden="true">S<span>&</span>F</span><div><strong>Sala<span>&</span>Fogón</strong><small>Gestión del restaurante</small></div></div>
        {perfil && <div className="profile-controls"><span className="profile-role">{perfil.rol === 'COCINERO' ? 'Cocina' : perfil.rol === 'ADMIN' ? 'Administración' : 'Sala'}</span><span className="profile-name">{perfil.nombre}</span><button className="button button-header" type="button" disabled={ocupado} onClick={salir}>Salir</button></div>}
      </div></header>
    <main className={`page${perfil ? '' : ' login-page'}`}>
      {!perfil ? (
        <form className="panel login-panel" onSubmit={ingresar}>
          <span className="eyebrow">Acceso del personal</span><h1>Bienvenido a Sala&Fogón</h1>
          <p>Ingresa para continuar con tu espacio de trabajo.</p>
          <label>Usuario <input autoComplete="username" value={usuario} onChange={(e) => setUsuario(e.target.value)} required /></label>
          <label>Contraseña <input type="password" autoComplete="current-password" value={clave} onChange={(e) => setClave(e.target.value)} required /></label>
          <button className="button button-primary login-submit" disabled={ocupado}>Ingresar</button>
          <p className="nota">Las credenciales se mantienen solo en esta pestaña durante la sesión.</p>
        </form>
      ) : (
        <>
          <div className="page-intro"><span className="eyebrow">{perfil.rol === 'COCINERO' ? 'Operación de cocina' : perfil.rol === 'ADMIN' ? 'Administración' : 'Servicio de sala'}</span><h1>{perfil.rol === 'COCINERO' ? 'Preparación de pedidos' : perfil.rol === 'ADMIN' ? 'Configura tu restaurante' : 'Atención de mesas'}</h1><p>{perfil.rol === 'COCINERO' ? 'Avanza cada plato según su estado.' : perfil.rol === 'ADMIN' ? 'Organiza el catálogo, las mesas y el equipo.' : 'Abre una mesa, prepara el pedido y sigue su cuenta.'}</p></div>
          {perfil.rol === 'MESERO' && Object.values(errorSincronizacion).some(Boolean) && <p className="nota" role="status">Algunos datos no pudieron actualizarse. Se reintentará automáticamente sin perder tu pedido temporal.</p>}
          {perfil.rol === 'COCINERO' ? <Cocina autorizacion={autorizacion} avisar={avisar} /> : perfil.rol === 'ADMIN' ? <Administracion autorizacion={autorizacion} avisar={avisar} /> : <>
          <section className="panel mesa-panel">
            <div><span className="eyebrow">Mesa en atención</span><h2>Selecciona una mesa</h2><p className="section-description">Retoma una sesión propia o inicia una nueva atención.</p></div>
            <div className="mesa-controls"><label>Seleccionar mesa
              <select value={mesaId} disabled={ocupado} onChange={(e) => seleccionarMesa(e.target.value)}>
                <option value="">Elige una mesa</option>
                {mesas.map((mesa) => <option key={mesa.id} value={mesa.id}>Mesa {mesa.numero}{mesa.sesion_activa_id ? mesa.sesion_propia ? ' — sesión propia' : ' — ocupada' : ''}</option>)}
              </select>
            </label>
            {mesaSeleccionada && !mesaSeleccionada.sesion_activa_id && <button className="button button-primary" type="button" disabled={ocupado} onClick={abrirSesion}>Abrir sesión</button>}
            {mesaSeleccionada?.sesion_activa_id && !mesaSeleccionada.sesion_propia && <p className="notice">Esta mesa ya tiene una sesión activa.</p>}
            {sesionId && <span className="session-badge">Sesión activa · #{sesionId}</span>}</div>
          </section>
          {sesionId && <>
            <nav className="section-nav" aria-label="Secciones de la mesa"><a href="#catalogo">Catálogo y pedido</a><a href="#pedidos">Pedidos</a><a href="#cuenta">Cuenta</a></nav>
            <div className="mesero-grid" id="catalogo"><section className="panel catalog-panel">
              <div className="section-heading"><div><span className="eyebrow">Carta actual</span><h2>Platos</h2><p>La disponibilidad se comprueba de nuevo al enviar.</p></div></div>
              {platos.length === 0 && <div className="empty-state"><strong>Sin platos registrados</strong><p>El administrador puede añadir platos desde Configuración.</p></div>}
              <ul className="platos">
                {platos.map((plato) => <li key={plato.id}>
                  <div className="dish-info"><strong>{plato.nombre}</strong><span className="dish-price">{formatPrice(plato.precio)}</span><span className={`availability${plato.disponible ? ' is-available' : ' is-unavailable'}`}>{plato.disponible ? 'Disponible' : 'No disponible'}</span></div>
                  <div className="controles" aria-label={`Unidades de ${plato.nombre}`}>
                    <button className="stepper-button" type="button" aria-label={`Quitar ${plato.nombre}`} disabled={ocupado || !borrador[plato.id]} onClick={() => cambiarCantidad(plato.id, -1)}>−</button>
                    <output>{borrador[plato.id] || 0}</output>
                    <button className="stepper-button" type="button" aria-label={`Añadir ${plato.nombre}`} disabled={ocupado || !plato.disponible} onClick={() => cambiarCantidad(plato.id, 1)}>+</button>
                  </div>
                </li>)}
              </ul>
            </section><aside className="panel draft-panel"><span className="eyebrow">Antes de enviar</span><h2>Pedido temporal</h2>
              {lineasBorrador.length === 0 ? <p className="draft-empty">Añade platos del catálogo para preparar el pedido.</p> : <ul className="draft-lines">{lineasBorrador.map((plato) => <li key={plato.id}><span>{plato.nombre}</span><strong>× {borrador[plato.id]}</strong></li>)}</ul>}
              <p className="draft-total"><strong>{totalUnidades}</strong> {totalUnidades === 1 ? 'unidad' : 'unidades'} <small>Se guardará al confirmar el envío.</small></p>
              <label>Observaciones <textarea value={observaciones} onChange={(e) => setObservaciones(e.target.value)} placeholder="Indicaciones para cocina, si las hay" /></label>
              <button className="button button-primary button-full" type="button" disabled={ocupado || totalUnidades === 0} onClick={enviarPedido}>Enviar a cocina</button>
            </aside></div>
            <section className="workspace-section" id="pedidos"><div className="section-heading"><div><span className="eyebrow">Seguimiento</span><h2>Pedidos de esta sesión</h2><p>Incluye pedidos listos y cancelados.</p></div></div>
              {pedidosMesa.length === 0 && <div className="empty-state"><strong>Aún no hay pedidos</strong><p>Los pedidos enviados aparecerán aquí.</p></div>}
              <div className="order-grid">{pedidosMesa.map((pedido) => <article className="order-card" key={pedido.id}>
                <div className="order-card-header"><div><span className="eyebrow">Pedido de la sesión</span><h3>Pedido {pedido.numero_en_sesion}</h3></div><small>ID global #{pedido.id}</small></div>
                <span className="estado" data-estado={pedido.estado_general}>{etiquetaEstado(pedido.estado_general)}</span>
                <ul className="item-list">{pedido.items.map((item) => <li key={item.id}>
                  <div className="item-main"><strong>{item.plato}</strong><span className="estado" data-estado={item.estado}>{etiquetaEstado(item.estado)}</span></div>
                  {item.estado === 'EN_COLA' && !item.pagado && <button className="button button-danger-quiet" type="button" disabled={ocupado} onClick={() => cancelarItem(item.id, sesionId)}>Cancelar</button>}
                </li>)}</ul>
              </article>)}</div>
            </section>
            <div id="cuenta"><Cuenta key={sesionId} sesionId={sesionId} autorizacion={autorizacion} revision={revisionCuenta} alCerrar={sesionCerrada} avisar={avisar} /></div>
          </>}
          </>}
        </>
      )}
      <div>{mensaje && <p className="ok">{mensaje}</p>}{error && <p className="error">{error}</p>}</div>
    </main>
    </div>
  )
}

export default App
