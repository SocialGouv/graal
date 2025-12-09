import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireAdmin?: boolean
}

const Container = ({
  children,
  ...props
}: { children: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => (
  <div className={fr.cx('fr-container')} {...props}>
    {children}
  </div>
)

/**
 * Protected route component that handles authentication and authorization
 *
 * @param children - The content to render if authorized
 * @param requireAdmin - Whether admin privileges are required (default: false)
 *
 * @example
 * <ProtectedRoute requireAdmin>
 *   <AdminPage />
 * </ProtectedRoute>
 */
export const ProtectedRoute = ({
  children,
  requireAdmin = false
}: ProtectedRouteProps) => {
  const { isAdmin, isLoading, error } = useAuth()

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <Container>
        <div className={fr.cx('fr-py-6w')}>
          <p>Chargement...</p>
        </div>
      </Container>
    )
  }

  // Show error state if authentication check failed
  if (error) {
    return (
      <Container>
        <div className={fr.cx('fr-py-6w')}>
          <Alert
            severity="error"
            title="Erreur d'authentification"
            description={error}
          />
        </div>
      </Container>
    )
  }

  // Redirect to home if admin access required but user is not admin
  // Only redirect when we're certain: not loading, no error, and not authorized
  if (requireAdmin && !isAdmin) {
    return <Navigate to="/" replace />
  }

  // Render children if authorized
  return <>{children}</>
}
