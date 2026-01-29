import { fr } from '@codegouvfr/react-dsfr'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { useNavigate } from 'react-router-dom'
import { ExcelConfigManager } from '../components/ExcelConfigManager/ExcelConfigManager'

export const ExcelConfigsPage = () => {
  const navigate = useNavigate()

  return (
    <div className={fr.cx('fr-container', 'fr-py-6w')}>
      <main>
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

        <ExcelConfigManager />
      </main>
    </div>
  )
}
