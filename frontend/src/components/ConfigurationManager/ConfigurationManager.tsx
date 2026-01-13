import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Badge } from '@codegouvfr/react-dsfr/Badge'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type ReactNode } from 'react'
import apiService from '../../services/api'
import type { ProcessingConfig } from '../../stores/processingStore'
import type { UserConfigurationRead } from '../../types/api'
import {
  UserConfigDeleteConfirmModal,
  UserConfigUnsavedChangesModal,
  userConfigDeleteConfirmModal,
  userConfigUnsavedChangesModal
} from './ConfigurationModals'

interface ConfigurationManagerProps {
  currentConfig: ProcessingConfig
  onConfigurationLoad: (config: ProcessingConfig) => void
}

export const ConfigurationManager = ({
  currentConfig,
  onConfigurationLoad
}: ConfigurationManagerProps) => {
  const queryClient = useQueryClient()
  const [loadedConfigId, setLoadedConfigId] = useState<string | null>(null)
  const [baselineConfig, setBaselineConfig] = useState<ProcessingConfig | null>(
    null
  )
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const [saveAsName, setSaveAsName] = useState('')
  const [showSaveAsForm, setShowSaveAsForm] = useState(false)

  const [pendingLoadConfig, setPendingLoadConfig] =
    useState<UserConfigurationRead | null>(null)
  const [deleteTargetConfig, setDeleteTargetConfig] =
    useState<UserConfigurationRead | null>(null)

  const cloneConfig = (config: ProcessingConfig): ProcessingConfig => {
    try {
      // structuredClone is available in modern browsers
      return structuredClone(config)
    } catch {
      // Fallback: config is JSON-compatible
      return JSON.parse(JSON.stringify(config)) as ProcessingConfig
    }
  }

  const stableStringify = (value: unknown): string => {
    if (value === undefined) return 'undefined'
    if (value === null) return 'null'
    if (typeof value !== 'object') return JSON.stringify(value)

    if (Array.isArray(value)) {
      return `[${value.map(stableStringify).join(',')}]`
    }

    const obj = value as Record<string, unknown>
    const keys = Object.keys(obj).sort()
    return `{${keys
      .map((k) => `${JSON.stringify(k)}:${stableStringify(obj[k])}`)
      .join(',')}}`
  }

  const isDirty =
    baselineConfig !== null &&
    stableStringify(currentConfig) !== stableStringify(baselineConfig)

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
    if (defaultConfig && !loadedConfigId) {
      handleLoadConfiguration(defaultConfig)
    }
  }, [defaultConfig, loadedConfigId])

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

  // Create configuration mutation
  const createMutation = useMutation({
    mutationFn: (data: {
      name: string
      feature_settings: Record<string, any>
      is_default: boolean
    }) => apiService.createUserConfiguration(data),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['userConfigurations'] })
      setSuccessMessage(`Configuration "${data.name}" créée avec succès`)
      setShowSaveAsForm(false)
      setSaveAsName('')
      setLoadedConfigId(data.id)
      setBaselineConfig(
        cloneConfig(variables.feature_settings as ProcessingConfig)
      )
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
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['userConfigurations'] })
      setSuccessMessage(`Configuration "${data.name}" mise à jour`)
      setBaselineConfig(
        cloneConfig(variables.updates.feature_settings as ProcessingConfig)
      )
    },
    onError: (error: any) => {
      setErrorMessage(
        error?.detail || 'Erreur lors de la mise à jour de la configuration'
      )
    }
  })

  // Keyboard shortcut handler (Ctrl+S or Cmd+S)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()

        if (loadedConfigId) {
          updateMutation.mutate({
            id: loadedConfigId,
            updates: {
              feature_settings: currentConfig as Record<string, any>
            }
          })
        } else {
          setShowSaveAsForm(true)
        }
      }
    }

    globalThis.addEventListener('keydown', handleKeyDown)
    return () => globalThis.removeEventListener('keydown', handleKeyDown)
  }, [currentConfig, loadedConfigId, updateMutation])

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
      userConfigDeleteConfirmModal.close()
      if (deleteTargetConfig?.id && deleteTargetConfig.id === loadedConfigId) {
        setLoadedConfigId(null)
        setBaselineConfig(null)
      }
      setDeleteTargetConfig(null)
    },
    onError: (error: any) => {
      setErrorMessage(
        error?.detail || 'Erreur lors de la suppression de la configuration'
      )
    }
  })

  const handleLoadConfiguration = (config: UserConfigurationRead) => {
    try {
      // Load feature settings into the form (without overwriting excel config)
      onConfigurationLoad(config.feature_settings as ProcessingConfig)
      setLoadedConfigId(config.id)
      setBaselineConfig(
        cloneConfig(config.feature_settings as ProcessingConfig)
      )
      setSuccessMessage(`Configuration "${config.name}" chargée`)
    } catch {
      setErrorMessage('Erreur lors du chargement de la configuration')
    }
  }

  const handleSaveAs = () => {
    if (!saveAsName.trim()) {
      setErrorMessage('Le nom de la configuration est requis')
      return
    }

    createMutation.mutate({
      name: saveAsName.trim(),
      feature_settings: currentConfig as Record<string, any>,
      is_default: false
    })
  }

  const confirmLoadConfiguration = (config: UserConfigurationRead) => {
    if (loadedConfigId && isDirty) {
      setPendingLoadConfig(config)
      userConfigUnsavedChangesModal.open()
      return
    }

    handleLoadConfiguration(config)
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

      {loadedConfigId && isDirty && (
        <p className={fr.cx('fr-text--sm', 'fr-mb-2w')}>
          <strong>Modifications non sauvegardées</strong>
        </p>
      )}

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

      {configurations.length === 0 ? (
        <div className={fr.cx('fr-py-4w')} style={{ textAlign: 'center' }}>
          <p className={fr.cx('fr-text--lead')}>Aucune configuration</p>
          <p className={fr.cx('fr-text--sm', 'fr-mb-0')}>
            Configurez le traitement puis cliquez sur « Enregistrer sous… ».
          </p>
        </div>
      ) : (
        <div className={fr.cx('fr-mt-2w')}>
          <Table
            headers={['Nom', 'Statut', 'Actions']}
            data={configurations.map((config) => {
              const isLoaded = loadedConfigId === config.id
              const actions: ReactNode[] = []

              if (!isLoaded) {
                actions.push(
                  <Button
                    key="load"
                    priority="secondary"
                    size="small"
                    onClick={() => confirmLoadConfiguration(config)}
                  >
                    Charger
                  </Button>
                )
              }

              if (!config.is_default) {
                actions.push(
                  <Button
                    key="default"
                    priority="tertiary no outline"
                    size="small"
                    iconId="fr-icon-star-line"
                    title="Définir par défaut"
                    nativeButtonProps={{
                      'aria-label': 'Définir par défaut'
                    }}
                    onClick={() => setDefaultMutation.mutate(config.id)}
                  >
                    <span className={fr.cx('fr-sr-only')}>
                      Définir par défaut
                    </span>
                  </Button>
                )
              }

              actions.push(
                <Button
                  key="delete"
                  priority="tertiary no outline"
                  size="small"
                  iconId="fr-icon-delete-line"
                  title="Supprimer"
                  nativeButtonProps={{
                    'aria-label': 'Supprimer'
                  }}
                  onClick={() => {
                    setDeleteTargetConfig(config)
                    userConfigDeleteConfirmModal.open()
                  }}
                >
                  <span className={fr.cx('fr-sr-only')}>Supprimer</span>
                </Button>
              )

              return [
                config.name,
                <ul
                  className={fr.cx('fr-badges-group', 'fr-badges-group--sm')}
                  style={{ margin: 0 }}
                >
                  {isLoaded && (
                    <li>
                      <Badge severity="success" noIcon small>
                        Chargée
                      </Badge>
                    </li>
                  )}
                  {config.is_default && (
                    <li>
                      <Badge severity="info" noIcon small>
                        Par défaut
                      </Badge>
                    </li>
                  )}
                  {!isLoaded && !config.is_default && <li>—</li>}
                </ul>,
                <div
                  key={config.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'flex-end',
                    alignItems: 'center',
                    gap: '0.5rem',
                    flexWrap: 'nowrap'
                  }}
                >
                  {actions}
                </div>
              ]
            })}
          />
        </div>
      )}

      {/* Save actions */}
      <div className={fr.cx('fr-mt-3w')}>
        <div className={fr.cx('fr-btns-group', 'fr-btns-group--inline-sm')}>
          {loadedConfigId && (
            <Button
              priority="primary"
              size="small"
              iconId="fr-icon-save-line"
              disabled={updateMutation.isPending || createMutation.isPending}
              onClick={() => {
                updateMutation.mutate({
                  id: loadedConfigId,
                  updates: {
                    feature_settings: currentConfig as Record<string, any>
                  }
                })
              }}
            >
              Sauvegarder
            </Button>
          )}

          <Button
            size="small"
            priority="secondary"
            disabled={createMutation.isPending}
            onClick={() => {
              setShowSaveAsForm(true)
              if (!saveAsName && loadedConfigId) {
                const loaded = configurations.find(
                  (c) => c.id === loadedConfigId
                )
                if (loaded?.name) setSaveAsName(`${loaded.name} (copie)`)
              }
            }}
          >
            Enregistrer sous…
          </Button>
        </div>

        {showSaveAsForm && (
          <div
            className={fr.cx('fr-mt-2w', 'fr-p-3w')}
            style={{
              backgroundColor: fr.colors.decisions.background.alt.grey.default
            }}
          >
            <h4 className={fr.cx('fr-h6', 'fr-mb-2w')}>
              Enregistrer une nouvelle configuration
            </h4>
            <Input
              label="Nom"
              nativeInputProps={{
                value: saveAsName,
                onChange: (e) => setSaveAsName(e.target.value),
                placeholder: 'Ex: Configuration PLFSS 2024'
              }}
            />
            <div
              className={fr.cx('fr-mt-3w')}
              style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}
            >
              <Button
                priority="primary"
                disabled={!saveAsName.trim() || createMutation.isPending}
                onClick={handleSaveAs}
              >
                Enregistrer
              </Button>
              <Button
                priority="secondary"
                onClick={() => {
                  setShowSaveAsForm(false)
                  setSaveAsName('')
                }}
              >
                Annuler
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Current status */}
      {loadedConfigId && (
        <div className={fr.cx('fr-mt-2w')}>
          <p className={fr.cx('fr-text--sm', 'fr-mb-0')}>
            <strong>Configuration chargée :</strong>{' '}
            {configurations.find((c) => c.id === loadedConfigId)?.name}
          </p>
        </div>
      )}

      {/* Modals */}
      <UserConfigDeleteConfirmModal
        configName={deleteTargetConfig?.name ?? 'cette configuration'}
        isDeleting={deleteMutation.isPending}
        onCancel={() => {
          userConfigDeleteConfirmModal.close()
          setDeleteTargetConfig(null)
        }}
        onConfirm={() => {
          if (!deleteTargetConfig?.id) return
          deleteMutation.mutate(deleteTargetConfig.id)
        }}
      />

      <UserConfigUnsavedChangesModal
        onCancel={() => {
          userConfigUnsavedChangesModal.close()
          setPendingLoadConfig(null)
        }}
        onConfirmLoseChanges={() => {
          if (!pendingLoadConfig) return
          userConfigUnsavedChangesModal.close()
          const toLoad = pendingLoadConfig
          setPendingLoadConfig(null)
          handleLoadConfiguration(toLoad)
        }}
      />
    </div>
  )
}
