import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { useAuth } from '../../hooks/useAuth'

const Container = ({
  children,
  ...props
}: { children: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => (
  <div className={fr.cx('fr-container')} {...props}>
    {children}
  </div>
)

export const Admin = () => {
  const { user, isAdmin, isLoading, error } = useAuth()

  if (isLoading) {
    return (
      <Container>
        <div className={fr.cx('fr-py-6w')}>
          <p>Chargement...</p>
        </div>
      </Container>
    )
  }

  if (error) {
    return (
      <Container>
        <div className={fr.cx('fr-py-6w')}>
          <Alert severity="error" title="Erreur" description={error} />
        </div>
      </Container>
    )
  }

  if (!isAdmin) {
    return (
      <Container>
        <div className={fr.cx('fr-py-6w')}>
          <Alert
            severity="warning"
            title="Accès refusé"
            description="Vous n'avez pas les permissions nécessaires pour accéder à cette page."
          />
        </div>
      </Container>
    )
  }

  return (
    <Container>
      <div className={fr.cx('fr-py-6w')}>
        <h1 className={fr.cx('fr-h2')}>You are admin!</h1>
        {user?.email && (
          <p className={fr.cx('fr-text--lead', 'fr-mt-2w')}>
            Email: {user.email}
          </p>
        )}
      </div>
    </Container>
  )
}
