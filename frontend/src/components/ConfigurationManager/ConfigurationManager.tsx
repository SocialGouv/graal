import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { RadioButtons } from '@codegouvfr/react-dsfr/RadioButtons'
import { Select } from '@codegouvfr/react-dsfr/Select'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import apiService from '../../services/api'
import type { ProcessingConfig } from '../../stores/processingStore'
import type { UserConfigurationRead } from '../../types/api'

interface ConfigurationManagerProps {
  currentConfig: ProcessingConfig
  selectedConfigFile: string | null
  onConfigurationLoad: (config: ProcessingConfig, configFile: string) => void
}

export const ConfigurationManager = ({
  currentConfig,
  selectedConfigFile,
  onConfigurationLoad
}: ConfigurationManagerProps) => {
  const queryClient = useQueryClient()
  const [selectedConfigId, setSelectedConfigId] = useState<string>('')
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [newConfigName, setNewConfigName] = useState('')
  const [saveMode, setSaveMode] = useState<'new' | 'overwrite'>('new')
  const [configToOverwrite, setConfigToOverwrite] = useState<string>('')
  const [loadedConfigId, setLoadedConfigId] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Fetch all user configurations
  const {
    data: configurations = [],
    isLoading,
    error: fetchError
  } = useQuery({
    queryKey: ['userConfigurations'],
    queryFn: () => apiService.getUserConfigurations(),
    staleTime: 30000 // Cache for 30 seconds
  })

  // Fetch default configuration on mount
  const { data: defaultConfig } = useQuery({
    queryKey: ['defaultConfiguration'],
    queryFn: () => apiService.getDefaultConfiguration(),
    retry: false, // Don't retry if no default exists
    staleTime: 30000
  })

  // Auto-load default configuration on mount
  useEffect(() => {
    if (defaultConfig && !loadedConfigId && selectedConfigFile) {
      handleLoadConfiguration(defaultConfig)
    }
  }, [defaultConfig, loadedConfigId, selectedConfigFile])

  // Clear messages after 5 seconds
  useEffect(() => {
    if (successMessage || errorMessage) {
      const timer = setTimeout(() => {
        setSuccessMessage(null)
        setErrorMessage(null)
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [successMessage, errorMessage])

  // Keyboard shortcut handler (Ctrl+S or Cmd+S)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        setShowSaveDialog(true)
        // Set default overwrite config if one is loaded
        if (loadedConfigId && saveMode === 'overwrite') {
          setConfigToOverwrite(loadedConfigId)
        }
      }
    }

    globalThis.addEventListener('keydown', handleKeyDown)
    return () => globalThis.removeEventListener('keydown', handleKeyDown)
  }, [loadedConfigId, saveMode])

  // Update configToOverwrite when loadedConfigId changes and mode is overwrite
  useEffect(() => {
    if (loadedConfigId && saveMode === 'overwrite' && !configToOverwrite) {
      setConfigToOverwrite(loadedConfigId)
    }
  }, [loadedConfigId, saveMode, configToOverwrite])

  // Create configuration mutation
  const createMutation = useMutation({
    mutationFn: (data: {
      name: string
      s3_config_file_path: string
      feature_settings: Record<string, any>
      is_default: boolean
    }) => apiService.createUserConfiguration(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['userConfigurations'] })
      setSuccessMessage(`Configuration "${data.name}" créée avec succès`)
      setShowSaveDialog(false)
      setNewConfigName('')
      setLoadedConfigId(data.id)
    },
    onError: (error: any) => {
      setErrorMessage(
        error?.detail || 'Erreur lors de la création de la configuration'
      )
    }
  })

  // Update configuration mutation
  const updateMutation = useMutation({
    mutationFn: (data: {
      id: string
      updates: { feature_settings: Record<string, any> }
    }) => apiService.updateUserConfiguration(data.id, data.updates),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['userConfigurations'] })
      setSuccessMessage(`Configuration "${data.name}" mise à jour`)
    },
    onError: (error: any) => {
      setErrorMessage(
        error?.detail || 'Erreur lors de la mise à jour de la configuration'
      )
    }
  })

  // Set default mutation
  const setDefaultMutation = useMutation({
    mutationFn: (id: string) => apiService.setDefaultConfiguration(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['userConfigurations'] })
      queryClient.invalidateQueries({ queryKey: ['defaultConfiguration'] })
      setSuccessMessage(`Configuration "${data.name}" définie par défaut`)
    },
    onError: (error: any) => {
      setErrorMessage(
        error?.detail ||
          'Erreur lors de la définition de la configuration par défaut'
      )
    }
  })

  // Delete configuration mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiService.deleteUserConfiguration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userConfigurations'] })
      queryClient.invalidateQueries({ queryKey: ['defaultConfiguration'] })
      setSuccessMessage('Configuration supprimée')
      if (loadedConfigId === selectedConfigId) {
        setLoadedConfigId(null)
      }
      setSelectedConfigId('')
    },
    onError: (error: any) => {
      setErrorMessage(
        error?.detail || 'Erreur lors de la suppression de la configuration'
      )
    }
  })

  const handleLoadConfiguration = (config: UserConfigurationRead) => {
    try {
      // Load feature settings into the form
      onConfigurationLoad(
        config.feature_settings as ProcessingConfig,
        config.s3_config_file_path
      )
      setLoadedConfigId(config.id)
      setSelectedConfigId(config.id)
      setSuccessMessage(`Configuration "${config.name}" chargée`)
    } catch {
      setErrorMessage('Erreur lors du chargement de la configuration')
    }
  }

  const handleSave = () => {
    if (saveMode === 'new') {
      if (!newConfigName.trim()) {
        setErrorMessage('Le nom de la configuration est requis')
        return
      }

      if (!selectedConfigFile) {
        setErrorMessage('Aucun fichier de configuration sélectionné')
        return
      }

      createMutation.mutate({
        name: newConfigName.trim(),
        s3_config_file_path: selectedConfigFile,
        feature_settings: currentConfig as Record<string, any>,
        is_default: false
      })
    } else {
      // Overwrite mode
      if (!configToOverwrite) {
        setErrorMessage('Veuillez sélectionner une configuration à écraser')
        return
      }

      updateMutation.mutate({
        id: configToOverwrite,
        updates: {
          feature_settings: currentConfig as Record<string, any>
        }
      })
    }
  }

  const handleSetDefault = () => {
    if (!selectedConfigId) return
    setDefaultMutation.mutate(selectedConfigId)
  }

  const handleDelete = () => {
    if (!selectedConfigId) return

    const config = configurations.find((c) => c.id === selectedConfigId)
    const confirmMessage = config
      ? `Êtes-vous sûr de vouloir supprimer la configuration "${config.name}" ?`
      : 'Êtes-vous sûr de vouloir supprimer cette configuration ?'

    if (globalThisconfirm(confirmMessage)) {
      deleteMutation.mutate(selectedConfigId)
    }
  }

  if (isLoading) {
    return (
      <div className={fr.cx('fr-mb-4w')}>
        <p>Chargement des configurations...</p>
      </div>
    )
  }

  return (
    <div className={fr.cx('fr-mb-4w')}>
      <h3 className={fr.cx('fr-h6', 'fr-mb-2w')}>
        Configurations sauvegardées
      </h3>

      {/* Success/Error messages */}
      {successMessage && (
        <Alert
          severity="success"
          title="Succès"
          description={successMessage}
          className={fr.cx('fr-mb-2w')}
          closable
          onClose={() => setSuccessMessage(null)}
        />
      )}

      {errorMessage && (
        <Alert
          severity="error"
          title="Erreur"
          description={errorMessage}
          className={fr.cx('fr-mb-2w')}
          closable
          onClose={() => setErrorMessage(null)}
        />
      )}

      {fetchError && (
        <Alert
          severity="warning"
          title="Avertissement"
          description="Impossible de charger les configurations sauvegardées"
          className={fr.cx('fr-mb-2w')}
        />
      )}

      {/* Configuration selector */}
      <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
        <div className={fr.cx('fr-col-12', 'fr-col-md-8')}>
          <Select
            label="Sélectionner une configuration"
            nativeSelectProps={{
              value: selectedConfigId,
              onChange: (e) => setSelectedConfigId(e.target.value)
            }}
          >
            <option value="">-- Choisir une configuration --</option>
            {configurations.map((config) => (
              <option key={config.id} value={config.id}>
                {config.name}
                {config.is_default ? ' (par défaut)' : ''}
                {loadedConfigId === config.id ? ' (chargée)' : ''}
              </option>
            ))}
          </Select>
        </div>

        <div
          className={fr.cx('fr-col-12', 'fr-col-md-4')}
          style={{ display: 'flex', alignItems: 'flex-end' }}
        >
          <Button
            priority="primary"
            disabled={!selectedConfigId}
            onClick={() => {
              const config = configurations.find(
                (c) => c.id === selectedConfigId
              )
              if (config) handleLoadConfiguration(config)
            }}
          >
            Charger
          </Button>
        </div>
      </div>

      {/* Action buttons */}
      <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters', 'fr-mt-2w')}>
        <div className={fr.cx('fr-col-12')}>
          <div
            style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}
            className={fr.cx('fr-btns-group', 'fr-btns-group--inline-sm')}
          >
            <Button
              priority="secondary"
              iconId="fr-icon-save-line"
              onClick={() => {
                setShowSaveDialog(!showSaveDialog)
                // Set default mode and config when opening dialog
                if (!showSaveDialog) {
                  if (loadedConfigId) {
                    setSaveMode('overwrite')
                    setConfigToOverwrite(loadedConfigId)
                  } else {
                    setSaveMode('new')
                  }
                }
              }}
            >
              Sauvegarder la configuration
            </Button>

            <Button
              priority="secondary"
              iconId="fr-icon-star-line"
              disabled={!selectedConfigId}
              onClick={handleSetDefault}
            >
              Définir par défaut
            </Button>

            <Button
              priority="secondary"
              iconId="fr-icon-delete-line"
              disabled={!selectedConfigId}
              onClick={handleDelete}
            >
              Supprimer
            </Button>
          </div>
        </div>
      </div>

      {/* Unified save configuration dialog */}
      {showSaveDialog && (
        <div
          className={fr.cx('fr-mt-3w', 'fr-p-3w')}
          style={{
            backgroundColor: fr.colors.decisions.background.alt.grey.default
          }}
        >
          <h4 className={fr.cx('fr-h6', 'fr-mb-2w')}>
            Sauvegarder la configuration actuelle
          </h4>

          {/* Save mode selection */}
          <RadioButtons
            legend="Mode de sauvegarde"
            options={[
              {
                label: 'Créer une nouvelle configuration',
                nativeInputProps: {
                  value: 'new',
                  checked: saveMode === 'new',
                  onChange: () => setSaveMode('new')
                }
              },
              {
                label: 'Écraser une configuration existante',
                nativeInputProps: {
                  value: 'overwrite',
                  checked: saveMode === 'overwrite',
                  onChange: () => {
                    setSaveMode('overwrite')
                    // Set default to loaded config if available
                    if (loadedConfigId && !configToOverwrite) {
                      setConfigToOverwrite(loadedConfigId)
                    }
                  }
                }
              }
            ]}
          />

          {/* New configuration name input */}
          {saveMode === 'new' && (
            <div className={fr.cx('fr-mt-2w')}>
              <Input
                label="Nom de la nouvelle configuration"
                nativeInputProps={{
                  value: newConfigName,
                  onChange: (e) => setNewConfigName(e.target.value),
                  placeholder: 'Ex: Configuration PLFSS 2024'
                }}
              />
            </div>
          )}

          {/* Overwrite configuration selection */}
          {saveMode === 'overwrite' && (
            <div className={fr.cx('fr-mt-2w')}>
              <Select
                label="Configuration à écraser"
                nativeSelectProps={{
                  value: configToOverwrite,
                  onChange: (e) => setConfigToOverwrite(e.target.value)
                }}
              >
                <option value="">-- Choisir une configuration --</option>
                {configurations.map((config) => (
                  <option key={config.id} value={config.id}>
                    {config.name}
                    {config.is_default ? ' (par défaut)' : ''}
                    {loadedConfigId === config.id ? ' (chargée)' : ''}
                  </option>
                ))}
              </Select>
            </div>
          )}

          {/* Action buttons */}
          <div
            className={fr.cx('fr-mt-3w')}
            style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}
          >
            <Button
              priority="primary"
              disabled={
                (saveMode === 'new' &&
                  (!newConfigName.trim() || createMutation.isPending)) ||
                (saveMode === 'overwrite' &&
                  (!configToOverwrite || updateMutation.isPending))
              }
              onClick={handleSave}
            >
              Sauvegarder
            </Button>

            <Button
              priority="secondary"
              onClick={() => {
                setShowSaveDialog(false)
                setNewConfigName('')
                setConfigToOverwrite('')
              }}
            >
              Annuler
            </Button>
          </div>
        </div>
      )}

      {/* Current status */}
      {loadedConfigId && (
        <div className={fr.cx('fr-mt-2w')}>
          <p className={fr.cx('fr-text--sm', 'fr-mb-0')}>
            <strong>Configuration chargée :</strong>{' '}
            {configurations.find((c) => c.id === loadedConfigId)?.name}
          </p>
        </div>
      )}
    </div>
  )
}
