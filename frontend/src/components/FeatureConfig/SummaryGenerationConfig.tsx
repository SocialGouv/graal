import { fr } from '@codegouvfr/react-dsfr'
import { Checkbox } from '@codegouvfr/react-dsfr/Checkbox'
import { Select } from '@codegouvfr/react-dsfr/Select'
import React from 'react'
import { useLlmConfigs } from '../../hooks/useS3Files'
import type { LlmConfigRead } from '../../types/api'

export interface SummaryGenerationConfigProps {
  shouldOverwrite: boolean
  llmConfigId: string | null
  onShouldOverwriteChange: (shouldOverwrite: boolean) => void
  onLlmConfigChange: (llmConfigId: string | null) => void
  enabled?: boolean
  disabled?: boolean
}

export const SummaryGenerationConfig: React.FC<
  SummaryGenerationConfigProps
> = ({
  shouldOverwrite,
  llmConfigId,
  onShouldOverwriteChange,
  onLlmConfigChange,
  enabled = false,
  disabled = false
}) => {
  const { data: llmConfigs = [], isLoading } = useLlmConfigs()
  const llmConfigError =
    enabled && !llmConfigId ? 'Sélectionnez une configuration LLM' : null

  const selectedConfig = llmConfigs.find(
    (config: LlmConfigRead) => config.id === llmConfigId
  )

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
      {/* LLM Config selector */}
      <div className={fr.cx('fr-mt-2w')}>
        <Select
          label="Configuration LLM"
          hint="Choisissez une configuration LLM existante"
          state={llmConfigError ? 'error' : 'default'}
          stateRelatedMessage={llmConfigError || undefined}
          nativeSelectProps={{
            value: llmConfigId || '',
            onChange: (e) => onLlmConfigChange(e.target.value || null),
            disabled,
            required: true
          }}
        >
          <option value="" disabled>
            {isLoading
              ? 'Chargement des configurations...'
              : 'Sélectionnez une configuration LLM'}
          </option>
          {llmConfigs.map((config) => (
            <option key={config.id} value={config.id}>
              {config.name} — {config.provider} — {config.model_name}
            </option>
          ))}
        </Select>
      </div>
      {selectedConfig && (
        <div className={fr.cx('fr-mt-2w')}>
          <p className={fr.cx('fr-text--sm', 'fr-mb-0')}>
            <strong>Configuration sélectionnée :</strong> {selectedConfig.name}{' '}
            — {selectedConfig.provider} — {selectedConfig.model_name}
          </p>
        </div>
      )}
    </>
  )
}

export default SummaryGenerationConfig
