import { startReactDsfr } from '@codegouvfr/react-dsfr/spa'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

startReactDsfr({
  defaultColorScheme: 'system',
  verbose: false
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
