import { useEffect, useRef } from 'react'

export const INTERVALO_OPERATIVO = 3000
export const INTERVALO_CONFIGURACION = 30000

// Comparte una lectura ya iniciada. Tras una escritura, force inicia una
// lectura nueva; el guard de la vista descarta la respuesta anterior.
export function createSingleFlight() {
  let actual = null
  return {
    run(clave, trabajo, { force = false } = {}) {
      if (!force && actual?.clave === clave) return actual.promesa
      const promesa = (async () => trabajo())()
      actual = { clave, promesa }
      const limpiar = () => { if (actual?.promesa === promesa) actual = null }
      promesa.then(limpiar, limpiar)
      return promesa
    },
  }
}

// Un único temporizador por recurso. La siguiente consulta comienza después
// de terminar la anterior; una pestaña oculta o sin conexión no consulta.
export function createAutoRefresh(refrescar, intervalo, entorno = {}) {
  const ventana = entorno.ventana ?? window
  const documento = entorno.documento ?? document
  const temporizadores = entorno.temporizadores ?? window
  const conectado = entorno.conectado ?? (() => navigator.onLine)
  let activo = false
  let enCurso = false
  let temporizador = null

  function detenerTemporizador() {
    if (temporizador !== null) temporizadores.clearTimeout(temporizador)
    temporizador = null
  }

  function sePuedeConsultar() {
    return activo && !documento.hidden && conectado()
  }

  function programar() {
    if (sePuedeConsultar() && !enCurso && temporizador === null) {
      temporizador = temporizadores.setTimeout(ejecutar, intervalo)
    }
  }

  async function ejecutar() {
    temporizador = null
    if (!sePuedeConsultar() || enCurso) return
    enCurso = true
    try {
      await refrescar()
    } catch {
      // Una falla temporal no detiene el ciclo; cada vista conserva sus datos
      // y decide si muestra un aviso discreto de sincronización.
    } finally {
      enCurso = false
      programar()
    }
  }

  function alVolver() {
    if (!sePuedeConsultar() || enCurso) return
    detenerTemporizador()
    void ejecutar()
  }

  function alCambiarVisibilidad() {
    if (documento.hidden) detenerTemporizador()
    else alVolver()
  }

  function alPerderConexion() { detenerTemporizador() }

  return {
    start() {
      if (activo) return
      activo = true
      ventana.addEventListener('focus', alVolver)
      ventana.addEventListener('online', alVolver)
      ventana.addEventListener('offline', alPerderConexion)
      documento.addEventListener('visibilitychange', alCambiarVisibilidad)
      programar()
    },
    stop() {
      activo = false
      detenerTemporizador()
      ventana.removeEventListener('focus', alVolver)
      ventana.removeEventListener('online', alVolver)
      ventana.removeEventListener('offline', alPerderConexion)
      documento.removeEventListener('visibilitychange', alCambiarVisibilidad)
    },
  }
}

export function useAutoRefresh(refrescar, intervalo, habilitado) {
  const refrescarActual = useRef(refrescar)
  refrescarActual.current = refrescar

  useEffect(() => {
    if (!habilitado) return undefined
    const control = createAutoRefresh(() => refrescarActual.current(), intervalo)
    control.start()
    return () => control.stop()
  }, [intervalo, habilitado])
}
