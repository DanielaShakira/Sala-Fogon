import { useEffect, useRef, useState } from 'react'
import { createLatestRequestGuard } from './latestRequest.js'
import { api } from './api.js'
import { formatCents, toCents } from './money.js'
import { etiquetaEstado } from './etiquetas.js'

export default function Cuenta({ sesionId, autorizacion, revision, alCerrar }) {
  const [cuenta, setCuenta] = useState(null)
  const [seleccionados, setSeleccionados] = useState([])
  const [ocupado, setOcupado] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  const guard = useRef(null)
  if (guard.current === null) guard.current = createLatestRequestGuard()

  async function refrescar({ conservarError = false } = {}) {
    const sigueVigente = guard.current.begin(sesionId)
    try {
      const datos = await api(`sesiones/${sesionId}/cuenta`, autorizacion)
      if (sigueVigente()) {
        setCuenta(datos)
        setSeleccionados((actual) => actual.filter((id) => datos.item_ids_pendientes.includes(id)))
        if (!conservarError) setError('')
      }
    } catch (fallo) {
      if (sigueVigente()) setError(fallo.message)
    }
  }

  useEffect(() => {
    guard.current.select(sesionId)
    setCuenta(null)
    setSeleccionados([])
    setMensaje('')
    void refrescar()
    return () => guard.current.select(null)
  }, [sesionId, autorizacion, revision])

  function alternar(id) {
    setSeleccionados((actual) => actual.includes(id)
      ? actual.filter((seleccionado) => seleccionado !== id)
      : [...actual, id])
  }

  async function registrar() {
    if (!cuenta || !cuenta.pago_habilitado || !seleccionados.length ||
        !seleccionados.every((id) => cuenta.item_ids_pendientes.includes(id))) return
    guard.current.invalidate()
    setOcupado(true)
    setError('')
    setMensaje('')
    let falloOperacion = null
    try {
      const pago = await api(`sesiones/${sesionId}/pagos`, autorizacion, {
        method: 'POST', body: JSON.stringify({ item_ids: seleccionados }),
      })
      if (guard.current.current() === sesionId) {
        setSeleccionados([])
        setMensaje(`Pago ${pago.id} registrado por $${pago.total}.`)
      }
    } catch (fallo) {
      falloOperacion = fallo
      if (guard.current.current() === sesionId) setError(fallo.message)
    } finally {
      if (guard.current.current() === sesionId) await refrescar({ conservarError: Boolean(falloOperacion) })
      setOcupado(false)
    }
  }

  async function cerrar() {
    if (!cuenta || cuenta.item_ids_pendientes.length) return
    guard.current.invalidate()
    setOcupado(true)
    setError('')
    try {
      await api(`sesiones/${sesionId}/cerrar`, autorizacion, { method: 'POST' })
      if (guard.current.current() === sesionId) alCerrar(sesionId)
    } catch (fallo) {
      if (guard.current.current() === sesionId) {
        setError(fallo.message)
        await refrescar({ conservarError: true })
      }
    } finally {
      setOcupado(false)
    }
  }

  const itemsSeleccionados = cuenta?.pedidos.flatMap((pedido) => pedido.items).filter(
    (item) => seleccionados.includes(item.id) && cuenta.item_ids_pendientes.includes(item.id)
  ) || []
  const importeSeleccionado = itemsSeleccionados.reduce(
    (total, item) => total + toCents(item.precio_unitario), 0n
  )

  return <section className="panel">
    <div className="cabecera"><h2>Cuenta de la sesión</h2><button type="button" disabled={ocupado} onClick={refrescar}>Actualizar</button></div>
    {!cuenta && !error && <p>Cargando cuenta...</p>}
    {cuenta && <>
      <p>Mesa {cuenta.mesa_numero} · Sesión {cuenta.sesion_id}</p>
      <p>Consumo: <strong>${cuenta.total_consumo}</strong> · Pagado: <strong>${cuenta.total_pagado}</strong> · Pendiente: <strong>${cuenta.total_pendiente}</strong></p>
      <p>Estado de la cuenta: <strong>{cuenta.estado_cuenta === 'PAGADA' ? 'Pagada' : 'Pendiente'}</strong></p>
      {!cuenta.pago_habilitado && <p className="nota">Los pagos se habilitan cuando todos los platos no cancelados estén listos.</p>}
      {cuenta.pedidos.map((pedido) => <article className="pedido" key={pedido.id}>
        <div className="cabecera pedido-cabecera"><h3>Pedido {pedido.numero_en_sesion}</h3><small>ID global {pedido.id}</small></div>
        <ul className="lista-items">{pedido.items.map((item) => <li key={item.id}>
          <span>{item.plato} · ${item.precio_unitario} · {etiquetaEstado(item.estado)} · {item.estado === 'CANCELADO' ? 'No facturable' : item.pago_id ? `Pagado en el pago ${item.pago_id}` : 'Pendiente de pago'}</span>
          {item.facturable && !item.pago_id && <label className="seleccion-pago"><input type="checkbox" checked={seleccionados.includes(item.id)} disabled={ocupado || !cuenta.pago_habilitado} onChange={() => alternar(item.id)} />Incluir</label>}
        </li>)}</ul>
      </article>)}
      {cuenta.pedidos.length === 0 && <p>Aún no hay consumo.</p>}
      <h3>Pagos registrados</h3>
      {cuenta.pagos.length === 0 ? <p>Aún no hay pagos.</p> : <ul>{cuenta.pagos.map((pago) => <li key={pago.id}>Pago {pago.id}: ${pago.total} · {pago.items.map((item) => item.plato).join(', ')}</li>)}</ul>}
      <p>Nuevo pago: {seleccionados.length} unidad(es) · <strong>{formatCents(importeSeleccionado)}</strong></p>
      <button type="button" disabled={ocupado || !cuenta.pago_habilitado || seleccionados.length === 0} onClick={registrar}>Registrar pago</button>
      <button type="button" disabled={ocupado || cuenta.item_ids_pendientes.length > 0} onClick={cerrar}>Cerrar sesión</button>
      {cuenta.item_ids_pendientes.length > 0 && <p className="nota">Para cerrar, asigna todas las unidades no canceladas a pagos.</p>}
    </>}
    <div aria-live="polite">{mensaje && <p className="ok">{mensaje}</p>}{error && <p className="error">{error}</p>}</div>
  </section>
}
