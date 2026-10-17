import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// Import Inter font (optional - system fonts will work as fallback)
// If you want to use Inter, uncomment and install: npm i @fontsource-variable/inter
// import '@fontsource-variable/inter'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
