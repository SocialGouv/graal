import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { S3FileBrowser } from './S3FileBrowser/S3FileBrowser'

const Container = ({
  children,
  ...props
}: { children: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => (
  <div className={fr.cx('fr-container')} {...props}>
    {children}
  </div>
)

export const Admin = () => {
  const navigate = useNavigate()
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
        {/* Back to Home Button */}
        <div className={fr.cx('fr-mb-4w')}>
          <Button
            priority="tertiary no outline"
            iconId="fr-icon-arrow-left-line"
            iconPosition="left"
            onClick={() => navigate('/')}
            size="small"
          >
            Retour à l'accueil
          </Button>
        </div>

        <h1 className={fr.cx('fr-h2', 'fr-mb-2w')}>Administration</h1>
        {user?.email && (
          <p className={fr.cx('fr-text--sm', 'fr-mb-6w')}>
            Connecté en tant que : {user.email}
          </p>
        )}
        <S3FileBrowser />
      </div>
    </Container>
  )
}
