import { useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import { createLatestRequestGuard } from './latestRequest.js'
import { createSingleFlight, INTERVALO_CONFIGURACION, useAutoRefresh } from './autoRefresh.js'

function Mesas({ mesas, ocupado, operar, autorizacion }) {
  const [numero, setNumero] = useState('')

  async function crear(evento) {
    evento.preventDefault()
    const correcto = await operar(() => api('configuracion/mesas', autorizacion, {
      method: 'POST', body: JSON.stringify({ numero: Number(numero) }),
    }), 'Mesa creada.')
    if (correcto) setNumero('')
  }

  return <section className="panel">
    <h2>Mesas</h2>
    <form className="formulario-en-linea" onSubmit={crear}>
      <label>Número de mesa <input type="number" min="1" step="1" required value={numero} onChange={(e) => setNumero(e.target.value)} /></label>
      <button disabled={ocupado}>Crear mesa</button>
    </form>
    {mesas.length === 0 ? <p>No hay mesas registradas.</p>
      : <p>{mesas.map((mesa) => `Mesa ${mesa.numero}`).join(' · ')}</p>}
  </section>
}

function IngredienteFila({ ingrediente, ocupado, operar, autorizacion }) {
  const [cantidadNueva, setCantidadNueva] = useState(ingrediente.cantidad_disponible)
  const cantidadAnterior = useRef(ingrediente.cantidad_disponible)
  useEffect(() => {
    setCantidadNueva((actual) => actual === cantidadAnterior.current
      ? ingrediente.cantidad_disponible : actual)
    cantidadAnterior.current = ingrediente.cantidad_disponible
  }, [ingrediente.cantidad_disponible])

  async function ajustar(evento) {
    evento.preventDefault()
    await operar(() => api(`configuracion/ingredientes/${ingrediente.id}/ajustar`, autorizacion, {
      method: 'POST', body: JSON.stringify({
        cantidad_esperada: ingrediente.cantidad_disponible,
        cantidad_nueva: cantidadNueva,
      }),
    }), `Existencias de ${ingrediente.nombre} actualizadas.`)
  }

  async function cambiarEstado() {
    await operar(() => api(`configuracion/ingredientes/${ingrediente.id}/estado`, autorizacion, {
      method: 'PATCH', body: JSON.stringify({ activo: !ingrediente.activo }),
    }), `${ingrediente.nombre}: ${ingrediente.activo ? 'desactivado' : 'activado'}.`)
  }

  return <li className="config-fila">
    <div><strong>{ingrediente.nombre}</strong> <small>#{ingrediente.id}</small><br />
      {ingrediente.activo ? 'Activo' : 'Inactivo'} · Existencia: {ingrediente.cantidad_disponible}</div>
    <div className="config-acciones">
      <form className="formulario-en-linea" onSubmit={ajustar}>
        <label>Nueva existencia total
          <input type="number" min="0" step="0.001" required value={cantidadNueva} onChange={(e) => setCantidadNueva(e.target.value)} />
        </label>
        <button disabled={ocupado}>Ajustar</button>
      </form>
      <button type="button" disabled={ocupado} onClick={cambiarEstado}>{ingrediente.activo ? 'Desactivar' : 'Activar'}</button>
    </div>
  </li>
}

function Ingredientes({ ingredientes, ocupado, operar, autorizacion }) {
  const [nombre, setNombre] = useState('')
  const [cantidad, setCantidad] = useState('0.000')

  async function crear(evento) {
    evento.preventDefault()
    const correcto = await operar(() => api('configuracion/ingredientes', autorizacion, {
      method: 'POST', body: JSON.stringify({ nombre, cantidad_disponible: cantidad, activo: true }),
    }), 'Ingrediente creado.')
    if (correcto) {
      setNombre('')
      setCantidad('0.000')
    }
  }

  return <section className="panel">
    <h2>Ingredientes</h2>
    <p className="nota">Las cantidades son porciones abstractas definidas por el restaurante. El ajuste establece una nueva existencia total y se rechaza si cambió desde la última consulta.</p>
    <form className="formulario-en-linea" onSubmit={crear}>
      <label>Nombre <input required maxLength={150} value={nombre} onChange={(e) => setNombre(e.target.value)} /></label>
      <label>Existencia inicial <input type="number" min="0" step="0.001" required value={cantidad} onChange={(e) => setCantidad(e.target.value)} /></label>
      <button disabled={ocupado}>Crear ingrediente</button>
    </form>
    {ingredientes.length === 0 && <p>No hay ingredientes registrados.</p>}
    <ul className="lista-items">{ingredientes.map((ingrediente) => <IngredienteFila
      key={ingrediente.id} ingrediente={ingrediente} ocupado={ocupado} operar={operar} autorizacion={autorizacion}
    />)}</ul>
  </section>
}

function Platos({ platos, ingredientes, ocupado, operar, autorizacion }) {
  const [editando, setEditando] = useState(null)
  const [nombre, setNombre] = useState('')
  const [precio, setPrecio] = useState('0.00')
  const [activo, setActivo] = useState(true)
  const [composicion, setComposicion] = useState([])

  function nuevo() {
    setEditando(null)
    setNombre('')
    setPrecio('0.00')
    setActivo(true)
    setComposicion([])
  }

  function editar(plato) {
    setEditando(plato.id)
    setNombre(plato.nombre)
    setPrecio(plato.precio)
    setActivo(plato.activo)
    setComposicion(plato.composicion.map((fila) => ({
      ingrediente_id: String(fila.ingrediente_id),
      cantidad_requerida: fila.cantidad_requerida,
    })))
  }

  function cambiarFila(indice, campo, valor) {
    setComposicion((actual) => actual.map((fila, posicion) =>
      posicion === indice ? { ...fila, [campo]: valor } : fila
    ))
  }

  async function guardar(evento) {
    evento.preventDefault()
    const datos = {
      nombre, precio, activo,
      composicion: composicion.map((fila) => ({
        ingrediente_id: Number(fila.ingrediente_id),
        cantidad_requerida: fila.cantidad_requerida,
      })),
    }
    const ruta = editando === null ? 'configuracion/platos' : `configuracion/platos/${editando}`
    const correcto = await operar(() => api(ruta, autorizacion, {
      method: editando === null ? 'POST' : 'PUT', body: JSON.stringify(datos),
    }), editando === null ? 'Plato creado.' : 'Plato y receta actualizados.')
    if (correcto) nuevo()
  }

  const nombres = Object.fromEntries(ingredientes.map((ingrediente) => [ingrediente.id, ingrediente.nombre]))

  return <section className="panel">
    <div className="cabecera"><h2>Platos y recetas</h2><button type="button" disabled={ocupado} onClick={nuevo}>Nuevo plato</button></div>
    {platos.length === 0 && <p>No hay platos registrados.</p>}
    <ul className="lista-items">{platos.map((plato) => <li key={plato.id}>
      <span><strong>{plato.nombre}</strong> · ${plato.precio} · {plato.activo ? 'Activo' : 'Inactivo'} · {plato.disponible ? 'Disponible' : 'No disponible'}<br />
        <small>Receta: {plato.composicion.length ? plato.composicion.map((fila) =>
          `${nombres[fila.ingrediente_id] || `Ingrediente #${fila.ingrediente_id}`} (${fila.cantidad_requerida})`
        ).join(', ') : 'sin ingredientes requeridos'}</small>
      </span>
      <button type="button" disabled={ocupado} onClick={() => editar(plato)}>Editar</button>
    </li>)}</ul>
    <form onSubmit={guardar} className="editor-plato">
      <h3>{editando === null ? 'Crear plato' : `Editar plato #${editando}`}</h3>
      <label>Nombre <input required maxLength={150} value={nombre} onChange={(e) => setNombre(e.target.value)} /></label>
      <label>Precio <input type="number" min="0" step="0.01" required value={precio} onChange={(e) => setPrecio(e.target.value)} /></label>
      <label className="casilla"><input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} /> Plato activo</label>
      <div className="cabecera"><h3>Ingredientes por unidad</h3><button type="button" disabled={ocupado || ingredientes.length === 0} onClick={() => setComposicion((actual) => [...actual, { ingrediente_id: '', cantidad_requerida: '1.000' }])}>Añadir ingrediente</button></div>
      {composicion.map((fila, indice) => <div className="fila-receta" key={indice}>
        <label>Ingrediente <select required value={fila.ingrediente_id} onChange={(e) => cambiarFila(indice, 'ingrediente_id', e.target.value)}>
          <option value="">Selecciona</option>
          {ingredientes.map((ingrediente) => <option value={ingrediente.id} key={ingrediente.id}>{ingrediente.nombre} (#{ingrediente.id})</option>)}
        </select></label>
        <label>Cantidad <input type="number" min="0.001" step="0.001" required value={fila.cantidad_requerida} onChange={(e) => cambiarFila(indice, 'cantidad_requerida', e.target.value)} /></label>
        <button type="button" disabled={ocupado} onClick={() => setComposicion((actual) => actual.filter((_, posicion) => posicion !== indice))}>Quitar</button>
      </div>)}
      <button disabled={ocupado}>{editando === null ? 'Crear plato' : 'Guardar cambios'}</button>
    </form>
  </section>
}

export default function Configuracion({ autorizacion, avisar }) {
  const [mesas, setMesas] = useState([])
  const [ingredientes, setIngredientes] = useState([])
  const [platos, setPlatos] = useState([])
  const [ocupado, setOcupado] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  const [errorSincronizacion, setErrorSincronizacion] = useState(false)
  const guard = useRef(null)
  if (guard.current === null) guard.current = createLatestRequestGuard()
  const consulta = useRef(null)
  if (consulta.current === null) consulta.current = createSingleFlight()
  function reportarError(texto) { setError(texto); avisar('error', texto) }
  function reportarExito(texto) { setMensaje(texto); avisar('exito', texto) }

  function cargar({ silencioso = false, force = false } = {}) {
    return consulta.current.run(autorizacion, async () => {
      const vigente = guard.current.begin('configuracion')
      try {
        const [mesasNuevas, ingredientesNuevos, platosNuevos] = await Promise.all([
          api('configuracion/mesas', autorizacion),
          api('configuracion/ingredientes', autorizacion),
          api('configuracion/platos', autorizacion),
        ])
        if (vigente()) {
          setMesas(mesasNuevas)
          setIngredientes(ingredientesNuevos)
          setPlatos(platosNuevos)
          setErrorSincronizacion(false)
        }
      } catch (fallo) {
        if (vigente()) {
          if (silencioso) setErrorSincronizacion(true)
          else reportarError(fallo.message)
        }
      }
    }, { force })
  }

  useAutoRefresh(() => cargar({ silencioso: true }), INTERVALO_CONFIGURACION, !ocupado)

  useEffect(() => {
    guard.current.select('configuracion')
    void cargar({ force: true })
    return () => guard.current.select(null)
  }, [autorizacion])

  async function operar(accion, textoExito) {
    guard.current.invalidate()
    setOcupado(true)
    setError('')
    setMensaje('')
    let correcto = false
    try {
      await accion()
      reportarExito(textoExito)
      correcto = true
    } catch (fallo) {
      reportarError(fallo.message)
    } finally {
      await cargar({ force: true })
      setOcupado(false)
    }
    return correcto
  }

  return <>
    <div className="cabecera"><h2>Configuración del restaurante</h2></div>
    {errorSincronizacion && <p className="nota" role="status">No se pudo actualizar la configuración. Se reintentará automáticamente.</p>}
    <Mesas mesas={mesas} ocupado={ocupado} operar={operar} autorizacion={autorizacion} />
    <Ingredientes ingredientes={ingredientes} ocupado={ocupado} operar={operar} autorizacion={autorizacion} />
    <Platos platos={platos} ingredientes={ingredientes} ocupado={ocupado} operar={operar} autorizacion={autorizacion} />
    <div>{mensaje && <p className="ok">{mensaje}</p>}{error && <p className="error">{error}</p>}</div>
  </>
}
