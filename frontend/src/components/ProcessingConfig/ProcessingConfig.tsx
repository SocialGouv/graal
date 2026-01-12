import { fr } from '@codegouvfr/react-dsfr'
import { Accordion } from '@codegouvfr/react-dsfr/Accordion'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Select } from '@codegouvfr/react-dsfr/Select'
import React, { useMemo } from 'react'
import { DEFAULT_FEATURE_FLAGS } from '../../config/featureFlags'
import { useValidation } from '../../hooks/useValidation'
import { useProcessingStore } from '../../stores/processingStore'
import {
  ColumnsToCopyConfig,
  FeatureConfigSection,
  ProjectSelectionConfig,
  SimpleToggleConfig,
  SummaryGenerationConfig
} from '../FeatureConfig'
import DatabaseSelectorConfig from '../FeatureConfig/DatabaseSelectorConfig'
import { COLUMN_OPTIONS, PROJECT_OPTIONS } from './constants/options'
import { useProcessingConfigHandlers } from './hooks/useProcessingConfigHandlers'

interface ProcessingConfigProps {
  disabled?: boolean
}

export const ProcessingConfig: React.FC<ProcessingConfigProps> = ({
  disabled = false
}) => {
  const { processingConfig, processingStatus } = useProcessingStore()
  const isProcessing =
    processingStatus !== 'idle' && processingStatus !== 'failed'

  // Use shared validation hook
  const { getOriginProjectError, getAllotmentsColumnError } = useValidation()

  // Use custom handlers hook
  const {
    handleAllotmentsEnabledChange,
    handleAllotmentsColumnChange,
    handleAttributionEnabledChange,
    handleAttributionProjectChange,
    handleAttributionShouldOverwriteChange,
    handleSimilaritySearchEnabledChange,
    handleSimilaritySearchOriginProjectChange,
    handleSimilaritySearchDatabaseIdChange,
    handleSimilaritySearchShouldOverwriteChange,
    handleColumnsToCopyChange,
    handleSimilaritiesWithinLecturesEnabledChange,
    handleSimilaritiesWithinLecturesColumnChange,
    handleDefaultOpinionEnabledChange,
    handleDefaultOpinionShouldOverwriteChange,
    handleSummaryGenerationEnabledChange,
    handleSummaryGenerationShouldOverwriteChange,
    handleSummaryGenerationLlmTypeChange,
    handleSummaryGenerationCredentialsChange,
    handlePlaceholderAmdtBodyChange
  } = useProcessingConfigHandlers()

  // Validation errors
  const similaritySearchOriginProjectError = useMemo(() => {
    if (!processingConfig.similaritySearch.enabled) {
      return null
    }

    return getOriginProjectError(
      processingConfig.similaritySearch.originProject ?? ''
    )
  }, [
    processingConfig.similaritySearch.enabled,
    processingConfig.similaritySearch.originProject,
    getOriginProjectError
  ])

  const similaritySearchDatabaseError = useMemo(() => {
    if (!processingConfig.similaritySearch.enabled) {
      return null
    }

    return processingConfig.similaritySearch.databaseId
      ? null
      : 'Veuillez sélectionner une base de données.'
  }, [
    processingConfig.similaritySearch.enabled,
    processingConfig.similaritySearch.databaseId
  ])

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

  return (
    <div>
      {/* Grid layout for main feature sections - 2 columns on desktop, 1 column on mobile */}
      <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
        {/* Left Column */}
        <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
          {/* Allotments Configuration Section */}
          <div className={fr.cx('fr-mb-4w')}>
            <FeatureConfigSection
              title="Activer le regroupement d'amendements (allotissement)"
              description="Groupe automatiquement les amendements similaires pour faciliter le traitement"
              enabled={processingConfig.allotments.enabled}
              onEnabledChange={handleAllotmentsEnabledChange}
              disabled={disabled || isProcessing}
            >
              <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
                <div className={fr.cx('fr-col-12')}>
                  <Select
                    label="Colonne à analyser"
                    hint="Choisissez la colonne utilisée pour comparer la similarité des amendements"
                    state={allotmentsColumnError ? 'error' : 'default'}
                    stateRelatedMessage={allotmentsColumnError || undefined}
                    nativeSelectProps={{
                      value: processingConfig.allotments.column,
                      onChange: (e) =>
                        handleAllotmentsColumnChange(e.target.value),
                      disabled: disabled || isProcessing
                    }}
                  >
                    {COLUMN_OPTIONS.map((option) => (
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
          <div className={fr.cx('fr-mb-4w')}>
            <FeatureConfigSection
              title="Attribution automatique"
              description="Assigne automatiquement les amendements aux réviseurs appropriés"
              enabled={processingConfig.attribution.enabled}
              onEnabledChange={handleAttributionEnabledChange}
              disabled={disabled || isProcessing}
            >
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
                projectOptions={PROJECT_OPTIONS}
                selectedProject={processingConfig.attribution.project_name}
                onProjectChange={handleAttributionProjectChange}
                disabled={disabled || isProcessing}
              />
            </FeatureConfigSection>
          </div>

          {/* Similarity Search Configuration Section */}
          <div className={fr.cx('fr-mb-4w')}>
            <FeatureConfigSection
              title="Recherche de similarités historiques"
              description="Trouve les amendements similaires dans les projets précédents"
              enabled={processingConfig.similaritySearch.enabled}
              onEnabledChange={handleSimilaritySearchEnabledChange}
              disabled={disabled || isProcessing}
            >
              <SimpleToggleConfig
                label="Écraser les valeurs existantes"
                description="Si activé, remplace les valeurs déjà présentes; si désactivé, préserve les valeurs existantes"
                checked={processingConfig.similaritySearch.should_overwrite}
                onChange={handleSimilaritySearchShouldOverwriteChange}
                disabled={disabled || isProcessing}
              />

              <div
                className={fr.cx(
                  'fr-grid-row',
                  'fr-grid-row--gutters',
                  'fr-mb-4w'
                )}
              >
                <div className={fr.cx('fr-col-12')}>
                  <Input
                    label="Nom du projet législatif"
                    hintText="Permet de faire aussi une recherche de similarité via le corps des amendements de lectures précédentes sur le même projet"
                    state={
                      similaritySearchOriginProjectError ? 'error' : 'default'
                    }
                    stateRelatedMessage={
                      similaritySearchOriginProjectError || undefined
                    }
                    nativeInputProps={{
                      placeholder: 'Ex: PLFSS 2025, PLF 2024...',
                      value:
                        processingConfig.similaritySearch.originProject || '',
                      onChange: (e) =>
                        handleSimilaritySearchOriginProjectChange(
                          e.target.value
                        ),
                      disabled: disabled || isProcessing,
                      maxLength: 100
                    }}
                  />
                </div>
              </div>

              <div>
                <DatabaseSelectorConfig
                  value={processingConfig.similaritySearch.databaseId}
                  onChange={handleSimilaritySearchDatabaseIdChange}
                  disabled={disabled || isProcessing}
                  validationError={similaritySearchDatabaseError}
                />
              </div>

              <div>
                <ColumnsToCopyConfig
                  columnsToCopy={
                    processingConfig.similaritySearch.columnsToCopy
                  }
                  onChange={handleColumnsToCopyChange}
                  disabled={disabled || isProcessing}
                  featureFlags={DEFAULT_FEATURE_FLAGS}
                />
              </div>
            </FeatureConfigSection>
          </div>
        </div>

        {/* Right Column */}
        <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
          {/* Similarities Within Lectures Configuration Section */}
          <div className={fr.cx('fr-mb-4w')}>
            <FeatureConfigSection
              title="Recherche de similarités intra-lecture"
              description="Trouve les amendements similaires au sein de la même session"
              enabled={processingConfig.similaritiesWithinLectures.enabled}
              onEnabledChange={handleSimilaritiesWithinLecturesEnabledChange}
              disabled={disabled || isProcessing}
            >
              <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
                <div className={fr.cx('fr-col-12')}>
                  <Select
                    label="Colonne à analyser"
                    hint="Colonne utilisée pour la comparaison des similarités intra-lecture"
                    state={
                      similaritiesWithinLecturesColumnError
                        ? 'error'
                        : 'default'
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
                    {COLUMN_OPTIONS.map((option) => (
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
          <div className={fr.cx('fr-mb-4w')}>
            <FeatureConfigSection
              title="Avis par défaut"
              description="Configure l'avis par défaut pour les amendements"
              enabled={processingConfig.defaultOpinion.enabled}
              onEnabledChange={handleDefaultOpinionEnabledChange}
              disabled={disabled || isProcessing}
            >
              <SimpleToggleConfig
                label="Écraser les valeurs existantes"
                description="Si activé, remplace les valeurs déjà présentes; si désactivé, préserve les valeurs existantes"
                checked={processingConfig.defaultOpinion.should_overwrite}
                onChange={handleDefaultOpinionShouldOverwriteChange}
                disabled={disabled || isProcessing}
              />
            </FeatureConfigSection>
          </div>
        </div>
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
              enabled={processingConfig.summaryGeneration.enabled}
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
