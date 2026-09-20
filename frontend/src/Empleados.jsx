import { useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import { createLatestRequestGuard } from './latestRequest.js'
import { createSingleFlight, INTERVALO_CONFIGURACION, useAutoRefresh } from './autoRefresh.js'
import { etiquetaRol } from './etiquetas.js'

export default function Empleados({ autorizacion, avisar }) {
  const [empleados, setEmpleados] = useState([])
  const [username, setUsername] = useState('')
  const [nombre, setNombre] = useState('')
  const [password, setPassword] = useState('')
  const [rol, setRol] = useState('MESERO')
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
      const vigente = guard.current.begin('empleados')
      try {
        const datos = await api('empleados', autorizacion)
        if (vigente()) {
          setEmpleados(datos)
          setErrorSincronizacion(false)
          if (!silencioso) setError('')
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
    guard.current.select('empleados')
    void cargar({ force: true })
    return () => guard.current.select(null)
  }, [autorizacion])

  async function crear(evento) {
    evento.preventDefault()
    guard.current.invalidate()
    setOcupado(true)
    setError('')
    setMensaje('')
    try {
      await api('empleados', autorizacion, {
        method: 'POST',
        body: JSON.stringify({ username, nombre, password, rol }),
      })
      setUsername('')
      setNombre('')
      setPassword('')
      reportarExito('Empleado creado y cuenta de acceso activada.')
      await cargar({ force: true })
    } catch (fallo) {
      reportarError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  async function cambiarEstado(empleado) {
    guard.current.invalidate()
    setOcupado(true)
    setError('')
    setMensaje('')
    try {
      await api(`empleados/${empleado.id}`, autorizacion, {
        method: 'PATCH', body: JSON.stringify({ activo: !empleado.activo }),
      })
      reportarExito(empleado.activo ? 'Cuenta desactivada.' : 'Cuenta activada.')
      await cargar({ force: true })
    } catch (fallo) {
      reportarError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  return <>
    <section className="panel">
      <h2>Crear empleado</h2>
      <form onSubmit={crear}>
        <label>Usuario <input autoComplete="off" value={username} onChange={(e) => setUsername(e.target.value)} required maxLength={150} /></label>
        <label>Nombre <input value={nombre} onChange={(e) => setNombre(e.target.value)} required maxLength={150} /></label>
        <label>Contraseña inicial <input type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        <label>Rol <select value={rol} onChange={(e) => setRol(e.target.value)}>
          <option value="MESERO">Mesero</option>
          <option value="COCINERO">Cocinero</option>
        </select></label>
        <button disabled={ocupado}>Crear cuenta</button>
      </form>
    </section>
    <section className="panel">
      <div className="cabecera"><h2>Empleados</h2></div>
      {errorSincronizacion && <p className="nota" role="status">No se pudo actualizar el personal. Se reintentará automáticamente.</p>}
      {empleados.length === 0 && <p>No hay empleados registrados.</p>}
      <ul className="lista-items empleados">
        {empleados.map((empleado) => <li key={empleado.id}>
          <span><strong>{empleado.nombre}</strong> · {empleado.username} · {etiquetaRol(empleado.rol)} · {empleado.activo ? 'Activo' : 'Inactivo'}</span>
          <button type="button" disabled={ocupado} onClick={() => cambiarEstado(empleado)}>{empleado.activo ? 'Desactivar' : 'Activar'}</button>
        </li>)}
      </ul>
    </section>
    <div>{mensaje && <p className="ok">{mensaje}</p>}{error && <p className="error">{error}</p>}</div>
  </>
}
