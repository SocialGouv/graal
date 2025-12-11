import { fr } from '@codegouvfr/react-dsfr'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { useNavigate } from 'react-router-dom'
import { DatabaseBuilder } from '../components/DatabaseBuilder'

export const DatabasePage = () => {
  const navigate = useNavigate()

  return (
    <div className={fr.cx('fr-container', 'fr-py-6w')}>
      <main>
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

        {/* Database Builder Component */}
        <DatabaseBuilder />
      </main>
    </div>
  )
}
