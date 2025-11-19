import { fr } from '@codegouvfr/react-dsfr'
import { Checkbox } from '@codegouvfr/react-dsfr/Checkbox'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Select } from '@codegouvfr/react-dsfr/Select'
import React, { useCallback } from 'react'

export interface SummaryGenerationConfigProps {
  shouldOverwrite: boolean
  llmType: 'scaleway' | 'albert' | 'ollama' | 'vllm' | 'fake' | 'mistral' | null
  llmCredentials: {
    base_url?: string
    api_key?: string
    model_name?: string
    endpoint?: string
    user?: string
    password?: string
  }
  onShouldOverwriteChange: (shouldOverwrite: boolean) => void
  onLlmTypeChange: (llmType: string) => void
  onCredentialsChange: (credentials: {
    base_url?: string
    api_key?: string
    model_name?: string
    endpoint?: string
    user?: string
    password?: string
  }) => void
  enabled?: boolean
  disabled?: boolean
}

export const SummaryGenerationConfig: React.FC<
  SummaryGenerationConfigProps
> = ({
  shouldOverwrite,
  llmType,
  llmCredentials,
  onShouldOverwriteChange,
  onLlmTypeChange,
  onCredentialsChange,
  enabled = false,
  disabled = false
}) => {
    const handleCredentialChange = useCallback(
      (field: string, value: string) => {
        onCredentialsChange({
          ...llmCredentials,
          [field]: value
        })
      },
      [llmCredentials, onCredentialsChange]
    )

    const llmTypeError = enabled && !llmType ? 'Sélectionnez un type de LLM' : null;

    // Determine which credential fields to show based on LLM type
    const showOpenAIFields =
      llmType === 'scaleway' || llmType === 'albert' || llmType === 'mistral'
    const showOllamaFields = llmType === 'ollama' || llmType === 'vllm'
    const showCredentialFields = llmType && llmType !== 'fake'

    return (
      <>
        {/* Should overwrite - at the top */}
        <div className={fr.cx('fr-mt-2w')}>
          <Checkbox
            options={[
              {
                label: 'Écraser les valeurs existantes',
                hintText:
                  'Si désactivé, les valeurs existantes dans Objet amdt seront préservées',
                nativeInputProps: {
                  checked: shouldOverwrite,
                  onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
                    onShouldOverwriteChange(e.target.checked),
                  disabled
                }
              }
            ]}
          />
        </div>
        {/* LLM Type selector */}
        <div className={fr.cx('fr-mt-2w')}>
          <Select
            label="Type de LLM"
            hint="Choisissez le fournisseur de LLM à utiliser"
            state={llmTypeError ? 'error' : 'default'}
            stateRelatedMessage={llmTypeError || undefined}
            nativeSelectProps={{
              value: llmType || '',
              onChange: (e) => onLlmTypeChange(e.target.value),
              disabled,
              required: true
            }}
          >
            <option value="" disabled>
              Sélectionnez un type de LLM
            </option>
            <option value="fake">Fake (pour les tests)</option>
            <option value="scaleway">Scaleway</option>
            <option value="albert">Albert (Etalab)</option>
            <option value="mistral">Mistral</option>
            <option value="ollama">Ollama</option>
            <option value="vllm">vLLM</option>
          </Select>
        </div>

        {/* Credentials - OpenAI-compatible (Scaleway, Albert) */}
        {showCredentialFields && showOpenAIFields && (
          <>
            <div className={fr.cx('fr-mt-2w')}>
              <Input
                label="Base URL"
                hintText="URL de base de l'API (ex: https://api.scaleway.ai/v1)"
                nativeInputProps={{
                  value: llmCredentials.base_url || '',
                  onChange: (e) =>
                    handleCredentialChange('base_url', e.target.value),
                  disabled,
                  required: true,
                  type: 'url'
                }}
              />
            </div>
            <div className={fr.cx('fr-mt-2w')}>
              <Input
                label="Clé API"
                hintText="Clé d'authentification API"
                nativeInputProps={{
                  value: llmCredentials.api_key || '',
                  onChange: (e) =>
                    handleCredentialChange('api_key', e.target.value),
                  disabled,
                  required: true,
                  type: 'password'
                }}
              />
            </div>
            <div className={fr.cx('fr-mt-2w')}>
              <Input
                label="Nom du modèle"
                hintText="Nom du modèle LLM à utiliser (ex: meta-llama/Meta-Llama-3.3-70B-Instruct)"
                nativeInputProps={{
                  value: llmCredentials.model_name || '',
                  onChange: (e) =>
                    handleCredentialChange('model_name', e.target.value),
                  disabled,
                  placeholder:
                    llmType === 'scaleway'
                      ? 'meta-llama/Meta-Llama-3.3-70B-Instruct'
                      : 'meta-llama/Meta-Llama-3.1-70B-Instruct'
                }}
              />
            </div>
          </>
        )}

        {/* Credentials - Ollama/vLLM */}
        {showCredentialFields && showOllamaFields && (
          <>
            <div className={fr.cx('fr-mt-2w')}>
              <Input
                label="Endpoint"
                hintText="URL du serveur Ollama/vLLM"
                nativeInputProps={{
                  value: llmCredentials.endpoint || '',
                  onChange: (e) =>
                    handleCredentialChange('endpoint', e.target.value),
                  disabled,
                  required: true,
                  type: 'url'
                }}
              />
            </div>
            <div className={fr.cx('fr-mt-2w')}>
              <Input
                label="Utilisateur"
                hintText="Nom d'utilisateur pour l'authentification"
                nativeInputProps={{
                  value: llmCredentials.user || '',
                  onChange: (e) => handleCredentialChange('user', e.target.value),
                  disabled,
                  required: true
                }}
              />
            </div>
            <div className={fr.cx('fr-mt-2w')}>
              <Input
                label="Mot de passe"
                hintText="Mot de passe pour l'authentification"
                nativeInputProps={{
                  value: llmCredentials.password || '',
                  onChange: (e) =>
                    handleCredentialChange('password', e.target.value),
                  disabled,
                  required: true,
                  type: 'password'
                }}
              />
            </div>
            <div className={fr.cx('fr-mt-2w')}>
              <Input
                label="Nom du modèle"
                hintText="Nom du modèle LLM à utiliser"
                nativeInputProps={{
                  value: llmCredentials.model_name || '',
                  onChange: (e) =>
                    handleCredentialChange('model_name', e.target.value),
                  disabled
                }}
              />
            </div>
          </>
        )}
      </>
    )
  }

export default SummaryGenerationConfig
