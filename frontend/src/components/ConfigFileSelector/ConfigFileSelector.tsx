import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { useQuery } from '@tanstack/react-query'
import { apiService } from '../../services/api'
import { useProcessingStore } from '../../stores/processingStore'
import { Combobox } from '../Combobox'

interface ConfigFileSelectorProps {
  disabled?: boolean
  /** Called with the manifest UUID (or null) when the selection changes */
  onChange?: (configId: string | null) => void
  /** The currently selected manifest UUID (or null) */
  value?: string | null
}

export const ConfigFileSelector: React.FC<ConfigFileSelectorProps> = ({
  disabled = false,
  onChange,
  value
}) => {
  const {
    selectedConfigFile,
    setSelectedConfigFile,
    setSelectedConfigFileName
  } = useProcessingStore()

  // Use provided value prop if given, otherwise fall back to store
  const currentValue = value !== undefined ? value : selectedConfigFile

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['excel-configs'],
    queryFn: () => apiService.listExcelConfigs(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3
  })

  const manifests = data?.configs ?? []

  // Index manifests by ID (for value→display lookup) and by file_name (for Combobox→ID lookup)
  const fileMetadataById = new Map(manifests.map((m) => [m.id, m]))
  const fileMetadataByName = new Map(manifests.map((m) => [m.file_name, m]))

  // Options shown in the Combobox are the human-readable file names
  const configFileNames = manifests.map((m) => m.file_name)

  // Translate the current UUID value back to a display name for the Combobox
  const currentDisplayValue = currentValue
    ? (fileMetadataById.get(currentValue)?.file_name ?? null)
    : null

  // The manifest corresponding to the currently selected ID (for metadata display)
  const selectedManifest = currentValue
    ? fileMetadataById.get(currentValue)
    : undefined

  /**
   * Called when the Combobox emits a file_name string (or null).
   * Translates to UUID and propagates via the external onChange or the store.
   */
  const handleComboboxChange = (fileName: string | null) => {
    if (!fileName) {
      if (onChange) {
        onChange(null)
      } else {
        setSelectedConfigFile(null)
        setSelectedConfigFileName(null)
      }
      return
    }

    const manifest = fileMetadataByName.get(fileName)
    const id = manifest?.id ?? null

    if (onChange) {
      // External caller (e.g. DatabaseBuilder) — just pass the ID
      onChange(id)
    } else {
      // Internal store — store both the ID and the display name
      setSelectedConfigFile(id)
      setSelectedConfigFileName(manifest?.file_name ?? null)
    }
  }

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
      <Combobox
        options={configFileNames}
        value={currentDisplayValue}
        onChange={handleComboboxChange}
        label="Fichier de configuration"
        hint="Sélectionnez un fichier de configuration que vous pouvez utiliser"
        state={error ? 'error' : 'default'}
        stateRelatedMessage={errorMessage}
        disabled={disabled}
        isLoading={isLoading}
        placeholder={placeholder}
        emptyMessage="Aucun fichier trouvé"
      />

      {selectedManifest && (
        <p className={fr.cx('fr-text--sm', 'fr-mt-1w')}>
          <strong>Rôle :</strong>{' '}
          {selectedManifest.current_user_role === 'owner'
            ? 'Propriétaire'
            : 'Lecteur'}
          <span className={fr.cx('fr-ml-1w')}>
            <strong>Ajouté le :</strong>{' '}
            {new Date(selectedManifest.created_at).toLocaleDateString('fr-FR')}
          </span>
        </p>
      )}

      {error && (
        <div className={fr.cx('fr-mt-2w')}>
          <Alert
            severity="error"
            title="Erreur"
            description="Le service de configuration n'est pas disponible."
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
