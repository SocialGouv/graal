import { startReactDsfr } from '@codegouvfr/react-dsfr/spa'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

const mode = import.meta.env.MODE ?? 'production'
const suffix =
  mode === 'development' ? 'dev' : mode === 'preprod' ? 'preprod' : null
document.title = suffix ? `GRAAL - ${suffix}` : 'GRAAL'

startReactDsfr({
  defaultColorScheme: 'system',
  verbose: false
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
