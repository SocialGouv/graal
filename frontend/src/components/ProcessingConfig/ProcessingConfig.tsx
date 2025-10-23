import { fr } from '@codegouvfr/react-dsfr'
import { Accordion } from '@codegouvfr/react-dsfr/Accordion'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Select } from '@codegouvfr/react-dsfr/Select'
import React, { useCallback, useMemo } from 'react'
import { DEFAULT_FEATURE_FLAGS } from '../../config/featureFlags'
import { useValidation } from '../../hooks/useValidation'
import { useProcessingStore } from '../../stores/processingStore'
import {
  ColumnsToCopyConfig,
  FeatureConfigSection,
  ProjectSelectionConfig,
  SimpleToggleConfig,
  SummaryGenerationConfig,
  type AttributionProjectOption,
  type ColumnOption
} from '../FeatureConfig'
import DatabaseSelectorConfig from '../FeatureConfig/DatabaseSelectorConfig'

interface ProcessingConfigProps {
  disabled?: boolean
}

export const ProcessingConfig: React.FC<ProcessingConfigProps> = ({
  disabled = false
}) => {
  const { processingConfig, setProcessingConfig, processingStatus } =
    useProcessingStore()
  const isProcessing =
    processingStatus !== 'idle' && processingStatus !== 'failed'

  // Use shared validation hook
  const { getOriginProjectError, getAllotmentsColumnError } = useValidation()

  const handleSimilaritySearchEnabledChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        similaritySearch: {
          ...processingConfig.similaritySearch,
          enabled: checked
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleSimilaritySearchOriginProjectChange = useCallback(
    (value: string) => {
      setProcessingConfig({
        ...processingConfig,
        similaritySearch: {
          ...processingConfig.similaritySearch,
          originProject: value
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleSimilaritySearchDatabaseFileChange = useCallback(
    (value: string | null) => {
      setProcessingConfig({
        ...processingConfig,
        similaritySearch: {
          ...processingConfig.similaritySearch,
          databaseFile: value
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  // Allotments handlers
  const handleAllotmentsEnabledChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        allotments: {
          ...processingConfig.allotments,
          enabled: checked
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleAllotmentsColumnChange = useCallback(
    (value: string) => {
      setProcessingConfig({
        ...processingConfig,
        allotments: {
          ...processingConfig.allotments,
          column: value as 'Corps amdt' | 'Exposé amdt'
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const similaritySearchOriginProjectError = useMemo(
    () =>
      processingConfig.similaritySearch.enabled &&
      processingConfig.similaritySearch.originProject
        ? getOriginProjectError(processingConfig.similaritySearch.originProject)
        : null,
    [
      processingConfig.similaritySearch.enabled,
      processingConfig.similaritySearch.originProject,
      getOriginProjectError
    ]
  )

  // Allotments validation
  const allotmentsColumnError = useMemo(
    () =>
      getAllotmentsColumnError(
        processingConfig.allotments.column,
        processingConfig.allotments.enabled
      ),
    [
      processingConfig.allotments.column,
      processingConfig.allotments.enabled,
      getAllotmentsColumnError
    ]
  )

  // SimilaritiesWithinLectures validation
  const similaritiesWithinLecturesColumnError = useMemo(
    () =>
      getAllotmentsColumnError(
        processingConfig.similaritiesWithinLectures.column,
        processingConfig.similaritiesWithinLectures.enabled
      ),
    [
      processingConfig.similaritiesWithinLectures.column,
      processingConfig.similaritiesWithinLectures.enabled,
      getAllotmentsColumnError
    ]
  )

  // Column options for dropdown
  const columnOptions: ColumnOption[] = useMemo(
    () => [
      { label: 'Corps amdt', value: 'Corps amdt' },
      { label: 'Exposé amdt', value: 'Exposé amdt' }
    ],
    []
  )

  // Project options for attribution
  const projectOptions: AttributionProjectOption[] = useMemo(
    () => [
      { label: 'PLF (Projet de Loi de Finances)', value: 'PLF' },
      {
        label: 'PLFSS (Projet de Loi de Financement de la Sécurité Sociale)',
        value: 'PLFSS'
      }
    ],
    []
  )

  // Additional handlers for new features
  const handleSimilaritiesWithinLecturesEnabledChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        similaritiesWithinLectures: {
          ...processingConfig.similaritiesWithinLectures,
          enabled: checked
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleAttributionEnabledChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        attribution: {
          ...processingConfig.attribution,
          enabled: checked
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleAttributionProjectChange = useCallback(
    (value: string) => {
      setProcessingConfig({
        ...processingConfig,
        attribution: {
          ...processingConfig.attribution,
          project_name: value
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )
  const handleSimilaritiesWithinLecturesColumnChange = useCallback(
    (value: string) => {
      setProcessingConfig({
        ...processingConfig,
        similaritiesWithinLectures: {
          ...processingConfig.similaritiesWithinLectures,
          column: value as 'Corps amdt' | 'Exposé amdt'
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  // should_overwrite handlers for each feature

  const handleSimilaritySearchShouldOverwriteChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        similaritySearch: {
          ...processingConfig.similaritySearch,
          should_overwrite: checked
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleAttributionShouldOverwriteChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        attribution: {
          ...processingConfig.attribution,
          should_overwrite: checked
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleDefaultOpinionShouldOverwriteChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        defaultOpinion: {
          ...processingConfig.defaultOpinion,
          should_overwrite: checked
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleColumnsToCopyChange = useCallback(
    (columnsToCopy: Record<string, any>) => {
      setProcessingConfig({
        ...processingConfig,
        similaritySearch: {
          ...processingConfig.similaritySearch,
          columnsToCopy
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handlePlaceholderAmdtBodyChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        placeholder_amdt_body: checked
      })
    },
    [setProcessingConfig, processingConfig]
  )

  // Summary Generation handlers
  const handleSummaryGenerationEnabledChange = useCallback(
    (enabled: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        summaryGeneration: {
          ...processingConfig.summaryGeneration,
          enabled
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleSummaryGenerationShouldOverwriteChange = useCallback(
    (shouldOverwrite: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        summaryGeneration: {
          ...processingConfig.summaryGeneration,
          should_overwrite: shouldOverwrite
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleSummaryGenerationLlmTypeChange = useCallback(
    (llmType: string) => {
      setProcessingConfig({
        ...processingConfig,
        summaryGeneration: {
          ...processingConfig.summaryGeneration,
          llm_type: llmType as any
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleSummaryGenerationCredentialsChange = useCallback(
    (credentials: any) => {
      setProcessingConfig({
        ...processingConfig,
        summaryGeneration: {
          ...processingConfig.summaryGeneration,
          llm_credentials: credentials
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  return (
    <div>
      <h3 className={fr.cx('fr-h6', 'fr-mb-2w')}>
        Configuration du traitement
      </h3>

      {/* Allotments Configuration Section */}
      <div className={fr.cx('fr-mt-4w')}>
        <FeatureConfigSection
          title="Activer le regroupement d'amendements (allotissement)"
          description="Groupe automatiquement les amendements similaires pour faciliter le traitement"
          enabled={processingConfig.allotments.enabled}
          onEnabledChange={handleAllotmentsEnabledChange}
          disabled={disabled || isProcessing}
        >
          <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
            <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
              <Select
                label="Colonne à analyser"
                hint="Choisissez la colonne utilisée pour comparer la similarité des amendements"
                state={allotmentsColumnError ? 'error' : 'default'}
                stateRelatedMessage={allotmentsColumnError || undefined}
                nativeSelectProps={{
                  value: processingConfig.allotments.column,
                  onChange: (e) => handleAllotmentsColumnChange(e.target.value),
                  disabled: disabled || isProcessing
                }}
              >
                {columnOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </FeatureConfigSection>
      </div>

      {/* Attribution Configuration Section */}
      <div className={fr.cx('fr-mt-4w')}>
        <FeatureConfigSection
          title="Attribution automatique"
          description="Assigne automatiquement les amendements aux réviseurs appropriés"
          enabled={processingConfig.attribution.enabled}
          onEnabledChange={handleAttributionEnabledChange}
          disabled={disabled || isProcessing}
        >
          {/* should_overwrite toggle for attribution */}
          <SimpleToggleConfig
            label="Écraser les valeurs existantes"
            description="Si activé, remplace les valeurs déjà présentes; si désactivé, préserve les valeurs existantes"
            checked={processingConfig.attribution.should_overwrite}
            onChange={handleAttributionShouldOverwriteChange}
            disabled={disabled || isProcessing}
          />

          <ProjectSelectionConfig
            label="Type de projet"
            hint="Sélectionnez le type de projet pour l'attribution"
            projectOptions={projectOptions}
            selectedProject={processingConfig.attribution.project_name}
            onProjectChange={handleAttributionProjectChange}
            disabled={disabled || isProcessing}
          />
        </FeatureConfigSection>
      </div>

      {/* Similarity Search Configuration Section */}
      <div className={fr.cx('fr-mt-4w')}>
        <FeatureConfigSection
          title="Recherche de similarités historiques"
          description="Trouve les amendements similaires dans les projets précédents"
          enabled={processingConfig.similaritySearch.enabled}
          onEnabledChange={handleSimilaritySearchEnabledChange}
          disabled={disabled || isProcessing}
        >
          {/* should_overwrite toggle for similarity search */}
          <SimpleToggleConfig
            label="Écraser les valeurs existantes"
            description="Si activé, remplace les valeurs déjà présentes; si désactivé, préserve les valeurs existantes"
            checked={processingConfig.similaritySearch.should_overwrite}
            onChange={handleSimilaritySearchShouldOverwriteChange}
            disabled={disabled || isProcessing}
          />

          {/* Origin Project */}
          <div
            className={fr.cx('fr-grid-row', 'fr-grid-row--gutters', 'fr-mb-4w')}
          >
            <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
              <Input
                label="Nom du projet législatif"
                hintText="Permet de faire aussi une recherche de similarité via le corps des amendements de lectures précédentes sur le même projet"
                state={similaritySearchOriginProjectError ? 'error' : 'default'}
                stateRelatedMessage={
                  similaritySearchOriginProjectError || undefined
                }
                nativeInputProps={{
                  placeholder: 'Ex: PLFSS 2025, PLF 2024...',
                  value: processingConfig.similaritySearch.originProject || '',
                  onChange: (e) =>
                    handleSimilaritySearchOriginProjectChange(e.target.value),
                  disabled: disabled || isProcessing,
                  maxLength: 100
                }}
              />
            </div>
          </div>

          {/* Database Selector */}
          <div>
            <DatabaseSelectorConfig
              value={processingConfig.similaritySearch.databaseFile}
              onChange={handleSimilaritySearchDatabaseFileChange}
              disabled={disabled || isProcessing}
            />
          </div>

          {/* Columns to Copy */}
          <div>
            <ColumnsToCopyConfig
              columnsToCopy={processingConfig.similaritySearch.columnsToCopy}
              onChange={handleColumnsToCopyChange}
              disabled={disabled || isProcessing}
              featureFlags={DEFAULT_FEATURE_FLAGS}
            />
          </div>
        </FeatureConfigSection>
      </div>

      {/* Similarities Within Lectures Configuration Section */}
      <div className={fr.cx('fr-mt-4w')}>
        <FeatureConfigSection
          title="Recherche de similarités intra-lecture"
          description="Trouve les amendements similaires au sein de la même session"
          enabled={processingConfig.similaritiesWithinLectures.enabled}
          onEnabledChange={handleSimilaritiesWithinLecturesEnabledChange}
          disabled={disabled || isProcessing}
        >
          <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
            <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
              <Select
                label="Colonne à analyser"
                hint="Colonne utilisée pour la comparaison des similarités intra-lecture"
                state={
                  similaritiesWithinLecturesColumnError ? 'error' : 'default'
                }
                stateRelatedMessage={
                  similaritiesWithinLecturesColumnError || undefined
                }
                nativeSelectProps={{
                  value: processingConfig.similaritiesWithinLectures.column,
                  onChange: (e) =>
                    handleSimilaritiesWithinLecturesColumnChange(
                      e.target.value
                    ),
                  disabled: disabled || isProcessing
                }}
              >
                {columnOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </FeatureConfigSection>
      </div>

      {/* Default Opinion Configuration Section */}
      <div className={fr.cx('fr-mt-4w')}>
        <FeatureConfigSection
          title="Avis par défaut"
          description="Configure l'avis par défaut pour les amendements"
          enabled={processingConfig.defaultOpinion.enabled}
          onEnabledChange={(checked) =>
            setProcessingConfig({
              ...processingConfig,
              defaultOpinion: {
                ...processingConfig.defaultOpinion,
                enabled: checked
              }
            })
          }
          disabled={disabled || isProcessing}
        >
          {/* should_overwrite toggle for default opinion */}
          <SimpleToggleConfig
            label="Écraser les valeurs existantes"
            description="Si activé, remplace les valeurs déjà présentes; si désactivé, préserve les valeurs existantes"
            checked={processingConfig.defaultOpinion.should_overwrite}
            onChange={handleDefaultOpinionShouldOverwriteChange}
            disabled={disabled || isProcessing}
          />
        </FeatureConfigSection>
      </div>

      {/* Summary Generation Configuration Section */}
      {DEFAULT_FEATURE_FLAGS.showSummaryGeneration && (
        <div className={fr.cx('fr-mt-4w')}>
          <FeatureConfigSection
            title="Génération d'objets d'amendements (LLM)"
            description="Génère automatiquement des résumés (Objet amdt) pour les amendements en utilisant un LLM"
            enabled={processingConfig.summaryGeneration.enabled}
            onEnabledChange={handleSummaryGenerationEnabledChange}
            disabled={disabled || isProcessing}
          >
            <SummaryGenerationConfig
              shouldOverwrite={
                processingConfig.summaryGeneration.should_overwrite
              }
              llmType={processingConfig.summaryGeneration.llm_type}
              llmCredentials={
                processingConfig.summaryGeneration.llm_credentials
              }
              onShouldOverwriteChange={
                handleSummaryGenerationShouldOverwriteChange
              }
              onLlmTypeChange={handleSummaryGenerationLlmTypeChange}
              onCredentialsChange={handleSummaryGenerationCredentialsChange}
              disabled={disabled || isProcessing}
            />
          </FeatureConfigSection>
        </div>
      )}

      {/* Advanced Configuration */}
      <div className={fr.cx('fr-mt-4w')}>
        <Accordion label="Configuration avancée" defaultExpanded={false}>
          <SimpleToggleConfig
            label="Texte de remplacement pour corps vide"
            description="Si activé, utilise un texte de remplacement pour les corps d'amendement vides"
            checked={processingConfig.placeholder_amdt_body}
            onChange={handlePlaceholderAmdtBodyChange}
            disabled={disabled || isProcessing}
          />
        </Accordion>
      </div>
    </div>
  )
}

export default ProcessingConfig
