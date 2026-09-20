import { useEffect, useRef } from 'react'

export default function AvisoGlobal({ aviso, alCerrar }) {
  const dialogo = useRef(null)

  useEffect(() => {
    if (!aviso || aviso.tipo === 'error') return undefined
    const temporizador = window.setTimeout(alCerrar, 6000)
    return () => window.clearTimeout(temporizador)
  }, [aviso, alCerrar])

  useEffect(() => {
    if (aviso?.tipo !== 'error') return undefined
    const elemento = dialogo.current
    elemento.showModal()
    return () => { if (elemento.open) elemento.close() }
  }, [aviso])

  if (!aviso) return null

  if (aviso.tipo === 'error') return <dialog ref={dialogo} className="error-dialog" role="alertdialog" aria-labelledby="error-dialog-title" aria-describedby="error-dialog-message" onCancel={(evento) => { evento.preventDefault(); alCerrar() }}>
    <span className="error-dialog-icon" aria-hidden="true">!</span>
    <h2 id="error-dialog-title">No se pudo completar la operación</h2>
    <p id="error-dialog-message">{aviso.texto}</p>
    <button className="button button-primary" type="button" autoFocus onClick={alCerrar}>Entendido</button>
  </dialog>

  return <div className="aviso-global aviso-global--exito" role="status">
    <div><strong>{aviso.tipo === 'listo' ? 'Aviso de cocina' : 'Operación completada'}</strong><p>{aviso.texto}</p></div>
    <button type="button" aria-label="Cerrar aviso" onClick={alCerrar}>×</button>
  </div>
}
