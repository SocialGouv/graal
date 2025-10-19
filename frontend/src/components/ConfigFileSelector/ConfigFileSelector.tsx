import { fr } from '@codegouvfr/react-dsfr'
import { Select } from '@codegouvfr/react-dsfr/Select'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { useQuery } from '@tanstack/react-query'
import { apiService } from '../../services/api'
import { useProcessingStore } from '../../stores/processingStore'

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

  const handleSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedValue = e.target.value
    handleChange(selectedValue || null)
  }

  return (
    <div className={fr.cx('fr-mb-4w')}>
      <Select
        label="Fichier de configuration"
        hint="Sélectionnez un fichier de configuration depuis S3"
        nativeSelectProps={{
          value: currentValue ?? '',
          onChange: handleSelect,
          disabled: disabled || isLoading
        }}
        state={error ? 'error' : 'default'}
        stateRelatedMessage={
          error
            ? 'Impossible de charger les fichiers de configuration'
            : undefined
        }
      >
        <option value="" disabled>
          -- Sélectionnez un fichier --
        </option>
        {data?.files.map((file) => (
          <option key={file} value={file}>
            {file}
          </option>
        ))}
      </Select>

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
