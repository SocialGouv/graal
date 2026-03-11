import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Badge } from '@codegouvfr/react-dsfr/Badge'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { createModal } from '@codegouvfr/react-dsfr/Modal'
import { Select } from '@codegouvfr/react-dsfr/Select'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { useMemo, useState } from 'react'
import {
  useAdminLlmConfigs,
  useCreateLlmConfig,
  useDeleteLlmConfig,
  useUpdateLlmConfig
} from '../../../hooks/useS3Files'
import type {
  LlmConfigCreate,
  LlmConfigRead,
  LlmProvider
} from '../../../types/api'

const editModal = createModal({
  id: 'admin-llm-config-edit-modal',
  isOpenedByDefault: false
})

type LlmConfigFormState = LlmConfigCreate

// `LlmConfigCreate` allows omitting `rate_limit_per_minute` (backend default),
// but in this admin form we always keep a concrete number in state.
type LlmConfigFormStateWithRequiredRateLimit = Omit<
  LlmConfigFormState,
  'rate_limit_per_minute'
> & {
  rate_limit_per_minute: number
  max_concurrent_requests: number
}

const defaultFormState: LlmConfigFormStateWithRequiredRateLimit = {
  name: '',
  provider: 'albert',
  model_name: '',
  base_url: '',
  api_key: '',
  rate_limit_per_minute: 500,
  max_concurrent_requests: 6
}

const providerLabels: Record<LlmProvider, string> = {
  albert: 'Albert'
  // scaleway: 'Scaleway',
  // mistral: 'Mistral',
  // ollama: 'Ollama',
  // vllm: 'vLLM'
}

const getDisplayLabel = (config: LlmConfigRead) =>
  `${config.name} — ${providerLabels[config.provider]} — ${config.model_name}`

export const AdminLlmConfigs = () => {
  const { data: configs = [], isLoading, error } = useAdminLlmConfigs()
  const createMutation = useCreateLlmConfig()
  const updateMutation = useUpdateLlmConfig()
  const deleteMutation = useDeleteLlmConfig()

  const [editingConfig, setEditingConfig] = useState<LlmConfigRead | null>(null)
  const [formState, setFormState] =
    useState<LlmConfigFormStateWithRequiredRateLimit>(defaultFormState)
  const [formError, setFormError] = useState<string | null>(null)

  const showError = Boolean(error)
  const isSaving = createMutation.isPending || updateMutation.isPending
  const isDeleting = deleteMutation.isPending

  const showOpenAIFields = formState.provider === 'albert'

  const resetForm = () => {
    setFormState(defaultFormState)
    setFormError(null)
  }

  const openCreateModal = () => {
    setEditingConfig(null)
    resetForm()
    editModal.open()
  }

  const openEditModal = (config: LlmConfigRead) => {
    setEditingConfig(config)
    setFormState({
      name: config.name,
      provider: config.provider,
      model_name: config.model_name,
      base_url: config.base_url ?? '',
      api_key: config.api_key ?? '',
      rate_limit_per_minute: config.rate_limit_per_minute,
      max_concurrent_requests: config.max_concurrent_requests
    })
    setFormError(null)
    editModal.open()
  }

  const handleFormChange = (
    field: keyof LlmConfigFormStateWithRequiredRateLimit,
    value: string | number
  ) => {
    setFormState((prev) => ({ ...prev, [field]: value }))
  }

  const validateForm = () => {
    if (!formState.name.trim()) {
      return 'Le nom est obligatoire.'
    }
    if (!formState.model_name.trim()) {
      return 'Le nom du modèle est obligatoire.'
    }
    if (showOpenAIFields && !formState.base_url?.trim()) {
      return 'La base URL est obligatoire pour ce fournisseur.'
    }
    if (showOpenAIFields && !formState.api_key?.trim()) {
      return 'La clé API est obligatoire pour ce fournisseur.'
    }

    const rateLimit = formState.rate_limit_per_minute

    if (!Number.isFinite(rateLimit) || rateLimit < 1 || rateLimit > 10000) {
      return 'La limite de requêtes/minute doit être comprise entre 1 et 10 000.'
    }

    const maxConcurrent = formState.max_concurrent_requests
    if (
      !Number.isFinite(maxConcurrent) ||
      maxConcurrent < 1 ||
      maxConcurrent > 100
    ) {
      return 'Le nombre maximum de requêtes concurrentes doit être compris entre 1 et 100.'
    }
    return null
  }

  const handleSubmit = async () => {
    const validationError = validateForm()
    if (validationError) {
      setFormError(validationError)
      return
    }

    const payload: LlmConfigCreate = {
      name: formState.name.trim(),
      provider: formState.provider,
      model_name: formState.model_name.trim(),
      base_url: showOpenAIFields ? formState.base_url?.trim() : undefined,
      api_key: showOpenAIFields ? formState.api_key?.trim() : undefined,
      rate_limit_per_minute: formState.rate_limit_per_minute,
      max_concurrent_requests: formState.max_concurrent_requests
    }

    try {
      if (editingConfig) {
        await updateMutation.mutateAsync({
          id: editingConfig.id,
          data: payload
        })
      } else {
        await createMutation.mutateAsync(payload)
      }
      editModal.close()
      resetForm()
      setEditingConfig(null)
    } catch (errorValue: any) {
      setFormError(
        errorValue?.detail ||
          "Une erreur est survenue lors de l'enregistrement."
      )
    }
  }

  const handleDelete = (config: LlmConfigRead) => {
    if (window.confirm(`Supprimer la configuration LLM « ${config.name} » ?`)) {
      deleteMutation.mutate(config.id)
    }
  }

  const tableRows = useMemo(
    () =>
      configs.map((config) => [
        config.name,
        <Badge key={`${config.id}-provider`} severity="info" noIcon small>
          {providerLabels[config.provider]}
        </Badge>,
        config.model_name,
        config.rate_limit_per_minute,
        config.max_concurrent_requests,
        new Date(config.updated_at).toLocaleDateString('fr-FR'),
        <div
          key={`${config.id}-actions`}
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            gap: '0.5rem',
            flexWrap: 'wrap'
          }}
        >
          <Button
            priority="secondary"
            size="small"
            onClick={() => openEditModal(config)}
          >
            Modifier
          </Button>
          <Button
            priority="tertiary no outline"
            size="small"
            iconId="fr-icon-delete-line"
            title="Supprimer"
            nativeButtonProps={{
              'aria-label': 'Supprimer'
            }}
            onClick={() => handleDelete(config)}
          >
            <span className={fr.cx('fr-sr-only')}>Supprimer</span>
          </Button>
        </div>
      ]),
    [configs]
  )

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '1rem',
          flexWrap: 'wrap'
        }}
      >
        <div>
          <h2 className={fr.cx('fr-h4', 'fr-mb-1v')}>Configurations LLM</h2>
          <p className={fr.cx('fr-text--sm', 'fr-mb-0')}>
            Gérez les configurations LLM globales disponibles dans les
            pipelines.
          </p>
        </div>
        <Button
          priority="primary"
          iconId="fr-icon-add-line"
          onClick={openCreateModal}
        >
          Ajouter
        </Button>
      </div>

      {showError && (
        <Alert
          severity="error"
          title="Erreur"
          description={
            (error as any)?.detail ||
            (error as any)?.message ||
            'Erreur lors du chargement'
          }
          className={fr.cx('fr-mt-3w')}
        />
      )}

      {deleteMutation.isError && (
        <Alert
          severity="error"
          title="Erreur de suppression"
          description={
            (deleteMutation.error as Error)?.message ||
            'Impossible de supprimer la configuration LLM'
          }
          className={fr.cx('fr-mt-3w')}
        />
      )}

      <div className={fr.cx('fr-mt-4w')}>
        {isLoading ? (
          <p>Chargement des configurations...</p>
        ) : configs.length > 0 ? (
          <Table
            headers={[
              'Nom',
              'Fournisseur',
              'Modèle',
              'Limite (req/min)',
              'Concurrence max',
              'Mis à jour',
              'Actions'
            ]}
            data={tableRows}
          />
        ) : (
          <p className={fr.cx('fr-text--sm')}>
            Aucune configuration LLM n'a été ajoutée.
          </p>
        )}
      </div>

      <editModal.Component title="Configuration LLM" size="large">
        <div className={fr.cx('fr-mb-2w')}>
          <p className={fr.cx('fr-text--sm')}>
            {editingConfig
              ? `Modifier : ${getDisplayLabel(editingConfig)}`
              : 'Créer une nouvelle configuration LLM.'}
          </p>
        </div>

        {formError && (
          <Alert
            severity="error"
            title="Erreur"
            description={formError}
            className={fr.cx('fr-mb-2w')}
          />
        )}

        <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
          <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
            <Input
              label="Nom"
              hintText="Libellé affiché dans la configuration de pipeline"
              nativeInputProps={{
                value: formState.name,
                onChange: (e) => handleFormChange('name', e.target.value)
              }}
            />
          </div>
          <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
            <Select
              label="Fournisseur"
              nativeSelectProps={{
                value: formState.provider,
                onChange: (e) =>
                  handleFormChange('provider', e.target.value as LlmProvider)
              }}
            >
              {Object.entries(providerLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div className={fr.cx('fr-mt-2w')}>
          <Input
            label="Nom du modèle"
            hintText="Ex: meta-llama/Meta-Llama-3.3-70B-Instruct"
            nativeInputProps={{
              value: formState.model_name,
              onChange: (e) => handleFormChange('model_name', e.target.value)
            }}
          />
        </div>

        {showOpenAIFields && (
          <div
            className={fr.cx('fr-grid-row', 'fr-grid-row--gutters', 'fr-mt-2w')}
          >
            <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
              <Input
                label="Base URL"
                hintText="Ex: https://api.scaleway.ai/v1"
                nativeInputProps={{
                  value: formState.base_url || '',
                  onChange: (e) => handleFormChange('base_url', e.target.value),
                  type: 'url'
                }}
              />
            </div>
            <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
              <Input
                label="Clé API"
                nativeInputProps={{
                  value: formState.api_key || '',
                  onChange: (e) => handleFormChange('api_key', e.target.value),
                  type: 'password'
                }}
              />
            </div>
          </div>
        )}

        <div className={fr.cx('fr-mt-2w')}>
          <Input
            label="Limite (requêtes/minute)"
            hintText="Entre 1 et 10 000"
            nativeInputProps={{
              value: String(formState.rate_limit_per_minute),
              onChange: (e) =>
                handleFormChange(
                  'rate_limit_per_minute',
                  Number(e.target.value)
                ),
              type: 'number',
              min: 1,
              max: 10000
            }}
          />
        </div>

        <div className={fr.cx('fr-mt-2w')}>
          <Input
            label="Concurrence maximale"
            hintText="Nombre maximum de requêtes simultanées (1 à 100)"
            nativeInputProps={{
              value: String(formState.max_concurrent_requests),
              onChange: (e) =>
                handleFormChange(
                  'max_concurrent_requests',
                  Number(e.target.value)
                ),
              type: 'number',
              min: 1,
              max: 100
            }}
          />
        </div>

        <div
          className={fr.cx('fr-mt-3w')}
          style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}
        >
          <Button priority="primary" onClick={handleSubmit} disabled={isSaving}>
            {isSaving ? 'Enregistrement...' : 'Enregistrer'}
          </Button>
          <Button
            priority="secondary"
            onClick={() => {
              editModal.close()
              resetForm()
              setEditingConfig(null)
            }}
            disabled={isSaving}
          >
            Annuler
          </Button>
          {isDeleting && (
            <span className={fr.cx('fr-text--sm')}>Suppression...</span>
          )}
        </div>
      </editModal.Component>
    </div>
  )
}
