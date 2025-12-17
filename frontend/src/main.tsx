import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

function App() {
  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Options Premium Analyzer</h1>
      <p>Frontend application is running successfully.</p>
      <p>API Base URL: {import.meta.env.VITE_API_URL || 'http://localhost:8000'}</p>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
