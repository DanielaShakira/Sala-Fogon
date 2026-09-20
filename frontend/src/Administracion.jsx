import { useState } from 'react'
import Empleados from './Empleados.jsx'
import Configuracion from './Configuracion.jsx'

export default function Administracion({ autorizacion, avisar }) {
  const [seccion, setSeccion] = useState('configuracion')

  return <>
    <nav className="pestanas" aria-label="Administración">
      <button type="button" aria-pressed={seccion === 'configuracion'} onClick={() => setSeccion('configuracion')}>Mesas y catálogo</button>
      <button type="button" aria-pressed={seccion === 'empleados'} onClick={() => setSeccion('empleados')}>Empleados</button>
    </nav>
    {seccion === 'configuracion'
      ? <Configuracion autorizacion={autorizacion} avisar={avisar} />
      : <Empleados autorizacion={autorizacion} avisar={avisar} />}
  </>
}
