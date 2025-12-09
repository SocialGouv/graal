import { Footer } from '@codegouvfr/react-dsfr/Footer'
import { Header } from '@codegouvfr/react-dsfr/Header'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

// Import pages
import { ProtectedRoute } from './components/ProtectedRoute'
import { AdminPage } from './pages/AdminPage'
import { DatabasePage } from './pages/DatabasePage'
import { Home } from './pages/Home'
import { ProcessingPage } from './pages/ProcessingPage'
import QueryProvider from './providers/QueryProvider'

function App() {
  return (
    <QueryProvider>
      <BrowserRouter>
        <Header
          brandTop={
            <>
              République
              <br />
              Française
            </>
          }
          serviceTitle="GRAAL"
          serviceTagline="Gestion et Répartition Automatisée des Amendements Législatifs"
          homeLinkProps={{
            href: '/',
            title: 'Accueil - GRAAL'
          }}
        />

        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/processing" element={<ProcessingPage />} />
          <Route path="/database" element={<DatabasePage />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute requireAdmin>
                <AdminPage />
              </ProtectedRoute>
            }
          />
        </Routes>

        <Footer
          brandTop={
            <>
              République
              <br />
              Française
            </>
          }
          accessibility="fully compliant"
          contentDescription="Application web pour le traitement automatisé des amendements législatifs"
          websiteMapLinkProps={{
            href: '#'
          }}
          accessibilityLinkProps={{
            href: '#'
          }}
          termsLinkProps={{
            href: '#'
          }}
        />
      </BrowserRouter>
    </QueryProvider>
  )
}

export default App
