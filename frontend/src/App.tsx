import { Footer } from '@codegouvfr/react-dsfr/Footer'
import { Header } from '@codegouvfr/react-dsfr/Header'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

// Import pages
import { JobsPoller } from './components/Jobs/JobsPoller'
import { ToastCenter } from './components/Jobs/ToastCenter'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AdminPage } from './pages/AdminPage'
import { DatabasePage } from './pages/DatabasePage'
import { ExcelConfigsPage } from './pages/ExcelConfigsPage'
import { Home } from './pages/Home'
import { ProcessingPage } from './pages/ProcessingPage'
import QueryProvider from './providers/QueryProvider'

function App() {
  return (
    <QueryProvider>
      <BrowserRouter>
        <JobsPoller />
        <ToastCenter />
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
          <Route
            path="/processing"
            element={
              <ProtectedRoute>
                <ProcessingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/database"
            element={
              <ProtectedRoute>
                <DatabasePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/excel-configs"
            element={
              <ProtectedRoute>
                <ExcelConfigsPage />
              </ProtectedRoute>
            }
          />
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
          accessibility="non compliant"
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
