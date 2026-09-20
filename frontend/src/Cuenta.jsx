import { useEffect, useRef, useState } from 'react'
import { createLatestRequestGuard } from './latestRequest.js'
import { createSingleFlight, INTERVALO_OPERATIVO, useAutoRefresh } from './autoRefresh.js'
import { api } from './api.js'
import { formatCents, toCents } from './money.js'
import { etiquetaEstado } from './etiquetas.js'

export default function Cuenta({ sesionId, autorizacion, revision, alCerrar, avisar }) {
  const [cuenta, setCuenta] = useState(null)
  const [seleccionados, setSeleccionados] = useState([])
  const [ocupado, setOcupado] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  const [errorSincronizacion, setErrorSincronizacion] = useState(false)
  const guard = useRef(null)
  if (guard.current === null) guard.current = createLatestRequestGuard()
  const consulta = useRef(null)
  if (consulta.current === null) consulta.current = createSingleFlight()
  const revisionAnterior = useRef(revision)
  function reportarError(texto) { setError(texto); avisar('error', texto) }
  function reportarExito(texto) { setMensaje(texto); avisar('exito', texto) }

  function refrescar({ conservarError = false, silencioso = false, force = false } = {}) {
    return consulta.current.run(`${autorizacion}:${sesionId}`, async () => {
      const sigueVigente = guard.current.begin(sesionId)
      try {
        const datos = await api(`sesiones/${sesionId}/cuenta`, autorizacion)
        if (sigueVigente()) {
          setCuenta(datos)
          setSeleccionados((actual) => actual.filter((id) => datos.item_ids_pendientes.includes(id)))
          setErrorSincronizacion(false)
          if (!silencioso && !conservarError) setError('')
        }
      } catch (fallo) {
        if (sigueVigente()) {
          if (silencioso) setErrorSincronizacion(true)
          else reportarError(fallo.message)
        }
      }
    }, { force })
  }

  useEffect(() => {
    guard.current.select(sesionId)
    setCuenta(null)
    setSeleccionados([])
    setMensaje('')
    void refrescar({ force: true })
    return () => guard.current.select(null)
  }, [sesionId, autorizacion])

  useEffect(() => {
    if (revisionAnterior.current === revision) return
    revisionAnterior.current = revision
    void refrescar({ silencioso: true, force: true })
  }, [revision])

  useAutoRefresh(() => refrescar({ silencioso: true }), INTERVALO_OPERATIVO, !ocupado)

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
        reportarExito(`Pago ${pago.id} registrado por $${pago.total}.`)
      }
    } catch (fallo) {
      falloOperacion = fallo
      if (guard.current.current() === sesionId) reportarError(fallo.message)
    } finally {
      if (guard.current.current() === sesionId) await refrescar({ conservarError: Boolean(falloOperacion), force: true })
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
        reportarError(fallo.message)
        await refrescar({ conservarError: true, force: true })
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

  return <section className="panel account-panel">
    <div className="section-heading">
      <div><span className="eyebrow">Cobro y cierre</span><h2>Cuenta de la sesión</h2>
        {cuenta && <p>Mesa {cuenta.mesa_numero} · Sesión #{cuenta.sesion_id}</p>}</div>
    </div>
    {errorSincronizacion && <p className="nota" role="status">No se pudo actualizar la cuenta. Se reintentará automáticamente.</p>}
    {!cuenta && !error && <p className="nota">Cargando cuenta...</p>}
    {cuenta && <>
      <div className="account-summary" aria-label="Resumen de la cuenta">
        <div className="stat"><small>Consumo</small><strong>${cuenta.total_consumo}</strong></div>
        <div className="stat"><small>Pagado</small><strong>${cuenta.total_pagado}</strong></div>
        <div className="stat stat-pending"><small>Pendiente</small><strong>${cuenta.total_pendiente}</strong></div>
      </div>
      <div className="account-status">
        <span className="eyebrow">Estado de la cuenta</span>
        <strong className={cuenta.estado_cuenta === 'PAGADA' ? 'account-paid' : 'account-unpaid'}>
          {cuenta.estado_cuenta === 'PAGADA' ? 'Pagada' : 'Pendiente'}
        </strong>
        {!cuenta.pago_habilitado && <p className="notice">Los pagos se habilitan cuando todos los platos no cancelados estén listos.</p>}
      </div>
      <div className="account-section-heading"><h3>Consumo de la sesión</h3><small>{cuenta.pedidos.length} {cuenta.pedidos.length === 1 ? 'pedido' : 'pedidos'}</small></div>
      {cuenta.pedidos.length === 0 && <div className="empty-state"><strong>Aún no hay consumo</strong><p>Los platos enviados a cocina aparecerán aquí.</p></div>}
      <div className="account-orders">{cuenta.pedidos.map((pedido) => <article className="order-card" key={pedido.id}>
        <div className="order-card-header"><div><span className="eyebrow">Consumo registrado</span><h3>Pedido {pedido.numero_en_sesion}</h3></div><small>ID global #{pedido.id}</small></div>
        <ul className="item-list">{pedido.items.map((item) => <li className="account-item" key={item.id}>
          <div className="account-item-main"><strong>{item.plato}</strong><small>{item.estado === 'CANCELADO' ? 'No facturable' : item.pago_id ? `Pagado en el pago ${item.pago_id}` : 'Pendiente de pago'}</small><span className="estado" data-estado={item.estado}>{etiquetaEstado(item.estado)}</span></div>
          <div className="account-item-side"><strong className="amount">${item.precio_unitario}</strong>
            {item.facturable && !item.pago_id && <label className="seleccion-pago"><input type="checkbox" checked={seleccionados.includes(item.id)} disabled={ocupado || !cuenta.pago_habilitado} onChange={() => alternar(item.id)} aria-label={`Incluir ${item.plato}, ítem ${item.id}, del pedido ${pedido.numero_en_sesion} en el pago`} /><span aria-hidden="true">Incluir</span></label>}
          </div>
        </li>)}</ul>
      </article>)}</div>
      <div className="account-bottom">
        <div className="payment-panel"><span className="eyebrow">Siguiente cobro</span><h3>Registrar pago</h3>
          <p className="nota">Selecciona las unidades pendientes de uno o varios pedidos.</p>
          <div className="payment-total"><span>{seleccionados.length} {seleccionados.length === 1 ? 'unidad seleccionada' : 'unidades seleccionadas'}</span><strong>{formatCents(importeSeleccionado)}</strong></div>
          <div className="payment-actions"><button className="button button-primary" type="button" disabled={ocupado || !cuenta.pago_habilitado || seleccionados.length === 0} onClick={registrar}>Registrar pago</button></div>
        </div>
        <div className="payments-history"><h3>Pagos registrados</h3>
          {cuenta.pagos.length === 0 ? <p className="nota">Aún no hay pagos.</p> : <ul>{cuenta.pagos.map((pago) => <li key={pago.id}><div className="payment-record"><strong>Pago {pago.id}</strong><strong className="amount">${pago.total}</strong></div><small>{pago.items.map((item) => item.plato).join(', ')}</small></li>)}</ul>}
        </div>
      </div>
      <div className="session-close"><div><span className="eyebrow">Finalizar atención</span><h3>Cerrar sesión</h3><p>{cuenta.item_ids_pendientes.length > 0 ? 'Para cerrar, asigna todas las unidades no canceladas a pagos.' : 'La cuenta está cubierta. La mesa quedará disponible para una nueva atención.'}</p></div>
        <button className="button button-secondary" type="button" disabled={ocupado || cuenta.item_ids_pendientes.length > 0} onClick={cerrar}>Cerrar sesión</button>
      </div>
    </>}
    <div>{mensaje && <p className="ok">{mensaje}</p>}{error && <p className="error">{error}</p>}</div>
  </section>
}
