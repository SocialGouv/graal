import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Button } from '@codegouvfr/react-dsfr/Button'

/**
 * Development-only login buttons.
 *
 * SECURITY: Only rendered when VITE_ENABLE_DEV_LOGIN=true.
 * NEVER enable this in preprod or production.
 */
export const DevLoginButtons = () => {
  if (import.meta.env.VITE_ENABLE_DEV_LOGIN !== 'true') {
    return null
  }

  const apiUrl = import.meta.env.VITE_API_URL || ''

  return (
    <div className={fr.cx('fr-mt-4w')}>
      <Alert
        severity="warning"
        title="Environnement de développement"
        description="Ces boutons de connexion rapide sont uniquement disponibles en environnement de développement et de recette."
        className={fr.cx('fr-mb-2w')}
      />
      <div className={fr.cx('fr-btns-group', 'fr-btns-group--inline')}>
        <Button
          linkProps={{ href: `${apiUrl}/api/v1/auth/dev-login?role=admin` }}
          iconId="fr-icon-shield-line"
        >
          Connexion Admin (dev)
        </Button>
        <Button
          linkProps={{ href: `${apiUrl}/api/v1/auth/dev-login?role=user` }}
          priority="secondary"
          iconId="fr-icon-user-line"
        >
          Connexion Utilisateur (dev)
        </Button>
      </div>
    </div>
  )
}
