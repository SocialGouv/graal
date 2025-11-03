import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { useQuery } from '@tanstack/react-query'
import { apiService } from '../../services/api'
import { useProcessingStore } from '../../stores/processingStore'
import { Combobox } from '../Combobox'

interface ConfigFileSelectorProps {
  disabled?: boolean
  onChange?: (filename: string | null) => void
  value?: string | null
}

export const ConfigFileSelector: React.FC<ConfigFileSelectorProps> = ({
  disabled = false,
  onChange,
  value
}) => {
  const { selectedConfigFile, setSelectedConfigFile } = useProcessingStore()

  // Use provided props if available, otherwise fall back to store
  const currentValue = value !== undefined ? value : selectedConfigFile
  const handleChange = onChange || setSelectedConfigFile

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['config-files'],
    queryFn: () => apiService.listConfigFiles(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3
  })

  const configFiles = data?.files || []

  const errorMessage = error
    ? 'Impossible de charger les fichiers de configuration'
    : undefined

  const placeholder = isLoading
    ? 'Chargement...'
    : error
      ? 'Erreur de chargement'
      : 'Tapez ou sélectionnez un fichier...'

  return (
    <div className={fr.cx('fr-mb-4w')}>
      <h3 className={fr.cx('fr-h6', 'fr-mb-2w')}>
        Sélection de la configuration
      </h3>

      <Combobox
        options={configFiles}
        value={currentValue}
        onChange={handleChange}
        label="Fichier de configuration"
        hint="Sélectionnez un fichier de configuration depuis S3"
        state={error ? 'error' : 'default'}
        stateRelatedMessage={errorMessage}
        disabled={disabled}
        isLoading={isLoading}
        placeholder={placeholder}
        emptyMessage="Aucun fichier trouvé"
      />

      {error && (
        <div className={fr.cx('fr-mt-2w')}>
          <Alert
            severity="error"
            title="Erreur"
            description="Le service de configuration S3 n'est pas disponible."
          />
          <Button
            priority="secondary"
            size="small"
            onClick={() => refetch()}
            className={fr.cx('fr-mt-2w')}
          >
            Réessayer
          </Button>
        </div>
      )}

      {isLoading && (
        <p className={fr.cx('fr-text--sm', 'fr-mt-1w')}>
          Chargement des fichiers de configuration...
        </p>
      )}
    </div>
  )
}
