import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [health, setHealth] = useState({ state: 'loading', message: 'Comprobando conexión…' })

  useEffect(() => {
    const controller = new AbortController()

    async function checkApi() {
      try {
        const response = await fetch('/api/health/', { signal: controller.signal })
        const result = await response.json()
        if (!response.ok || result.api !== 'ok' || result.database !== 'ok') {
          throw new Error('La API o PostgreSQL no está disponible.')
        }
        setHealth({ state: 'ok', message: 'API y PostgreSQL conectados.' })
      } catch (error) {
        if (error.name !== 'AbortError') {
          setHealth({ state: 'error', message: error.message })
        }
      }
    }

    checkApi()
    return () => controller.abort()
  }, [])

  return (
    <main className="page">
      <h1>Sala Fogón</h1>
      <p>Sistema de pedidos y cocina</p>
      <section className="status" aria-live="polite">
        <h2>Estado del entorno</h2>
        <p className={health.state}>{health.message}</p>
      </section>
    </main>
  )
}

export default App
