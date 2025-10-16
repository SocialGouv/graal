import React, { useCallback, useMemo } from 'react'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Accordion } from '@codegouvfr/react-dsfr/Accordion'
import { fr } from '@codegouvfr/react-dsfr'
import { useProcessingStore } from '../../stores/processingStore'
import { useValidation } from '../../hooks/useValidation'
import {
  FeatureConfigSection,
  ColumnSimilarityConfig,
  ProjectSelectionConfig,
  ThresholdSliderConfig,
  ColumnsToCopyConfig,
  SimpleToggleConfig,
  type ColumnOption,
  type ProjectOption
} from '../FeatureConfig'

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
  const {
    getOriginProjectError,
    getAllotmentsColumnError,
    getSimilarityThresholdError
  } = useValidation()

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

  const handleSimilarityThresholdChange = useCallback(
    (value: number) => {
      setProcessingConfig({
        ...processingConfig,
        allotments: {
          ...processingConfig.allotments,
          similarity_threshold: value
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

  // Similarity threshold validation
  const similarityThresholdError = useMemo(
    () =>
      getSimilarityThresholdError(
        processingConfig.allotments.similarity_threshold,
        processingConfig.allotments.enabled
      ),
    [
      processingConfig.allotments.similarity_threshold,
      processingConfig.allotments.enabled,
      getSimilarityThresholdError
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
  const similaritiesWithinLecturesThresholdError = useMemo(
    () =>
      getSimilarityThresholdError(
        processingConfig.similaritiesWithinLectures.similarity_threshold,
        processingConfig.similaritiesWithinLectures.enabled
      ),
    [
      processingConfig.similaritiesWithinLectures.similarity_threshold,
      processingConfig.similaritiesWithinLectures.enabled,
      getSimilarityThresholdError
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
  const projectOptions: ProjectOption[] = useMemo(
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
  const handleSimilaritiesWithinLecturesThresholdChange = useCallback(
    (value: number) => {
      setProcessingConfig({
        ...processingConfig,
        similaritiesWithinLectures: {
          ...processingConfig.similaritiesWithinLectures,
          similarity_threshold: value
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

  // Similarity search advanced handlers
  const handleClusteringThresholdChange = useCallback(
    (column: string, value: number) => {
      setProcessingConfig({
        ...processingConfig,
        similaritySearch: {
          ...processingConfig.similaritySearch,
          clusteringSimilarityThresholds: {
            ...processingConfig.similaritySearch.clusteringSimilarityThresholds,
            [column]: value
          }
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  const handleFuzzyMatchThresholdChange = useCallback(
    (column: string, value: number) => {
      setProcessingConfig({
        ...processingConfig,
        similaritySearch: {
          ...processingConfig.similaritySearch,
          fuzzyMatchSimilarityThresholds: {
            ...processingConfig.similaritySearch.fuzzyMatchSimilarityThresholds,
            [column]: value
          }
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

  return (
    <div className={fr.cx('fr-mb-4w')}>
      <h3 className={fr.cx('fr-h6', 'fr-mb-2w')}>
        Configuration du traitement
      </h3>

      {/* Similarity Search Configuration Section */}
      <div className={fr.cx('fr-mt-4w')}>
        <FeatureConfigSection
          title="Recherche de similarités historiques"
          description="Trouve les amendements similaires dans les projets précédents"
          enabled={processingConfig.similaritySearch.enabled}
          onEnabledChange={handleSimilaritySearchEnabledChange}
          disabled={disabled || isProcessing}
        >
          {/* Origin Project */}
          <div
            className={fr.cx('fr-grid-row', 'fr-grid-row--gutters', 'fr-mb-4w')}
          >
            <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
              <Input
                label="Projet d'origine"
                hintText="Nom du projet législatif (ex: PLFSS 2025, PLF 2024)"
                state={similaritySearchOriginProjectError ? 'error' : 'default'}
                stateRelatedMessage={
                  similaritySearchOriginProjectError || undefined
                }
                nativeInputProps={{
                  placeholder: 'Ex: PLFSS 2025',
                  value: processingConfig.similaritySearch.originProject || '',
                  onChange: (e) =>
                    handleSimilaritySearchOriginProjectChange(e.target.value),
                  disabled: disabled || isProcessing,
                  maxLength: 100
                }}
              />
            </div>
          </div>

          {/* Clustering Similarity Thresholds */}
          <div className={fr.cx('fr-mb-4w')}>
            <h4 className={fr.cx('fr-h6', 'fr-mb-2w')}>
              Seuils de similarité pour le clustering initial (TF-IDF)
            </h4>
            <p className={fr.cx('fr-text--sm', 'fr-mb-3w')}>
              Ces seuils sont utilisés pour le regroupement initial des
              amendements par similarité TF-IDF.
            </p>
            {Object.entries(
              processingConfig.similaritySearch.clusteringSimilarityThresholds
            ).map(([column, threshold]) => (
              <div key={`clustering-${column}`} className={fr.cx('fr-mb-2w')}>
                <ThresholdSliderConfig
                  label={`${column} - Clustering`}
                  hint={`Seuil de similarité TF-IDF pour la colonne "${column}"`}
                  value={threshold}
                  onChange={(value) =>
                    handleClusteringThresholdChange(column, value)
                  }
                  disabled={disabled || isProcessing}
                />
              </div>
            ))}
          </div>

          {/* Fuzzy Match Similarity Thresholds */}
          <div className={fr.cx('fr-mb-4w')}>
            <h4 className={fr.cx('fr-h6', 'fr-mb-2w')}>
              Seuils de similarité pour la correspondance précise
              (Damerau-Levenshtein)
            </h4>
            <p className={fr.cx('fr-text--sm', 'fr-mb-3w')}>
              Ces seuils sont utilisés pour la comparaison précise des
              amendements avec l'algorithme Damerau-Levenshtein.
            </p>
            {Object.entries(
              processingConfig.similaritySearch.fuzzyMatchSimilarityThresholds
            ).map(([column, threshold]) => (
              <div key={`fuzzy-${column}`} className={fr.cx('fr-mb-2w')}>
                <ThresholdSliderConfig
                  label={`${column} - Correspondance précise`}
                  hint={`Seuil de similarité Damerau-Levenshtein pour la colonne "${column}"`}
                  value={threshold}
                  onChange={(value) =>
                    handleFuzzyMatchThresholdChange(column, value)
                  }
                  disabled={disabled || isProcessing}
                />
              </div>
            ))}
          </div>

          {/* Columns to Copy */}
          <div className={fr.cx('fr-mb-4w')}>
            <ColumnsToCopyConfig
              columnsToCopy={processingConfig.similaritySearch.columnsToCopy}
              onChange={handleColumnsToCopyChange}
              disabled={disabled || isProcessing}
            />
          </div>

          {/* should_overwrite toggle for similarity search */}
          <SimpleToggleConfig
            label="Écraser les valeurs existantes"
            description="Si activé, remplace les valeurs déjà présentes; si désactivé, préserve les valeurs existantes"
            checked={processingConfig.similaritySearch.should_overwrite}
            onChange={handleSimilaritySearchShouldOverwriteChange}
            disabled={disabled || isProcessing}
          />
        </FeatureConfigSection>
      </div>

      {/* Allotments Configuration Section */}
      <div className={fr.cx('fr-mt-4w')}>
        <FeatureConfigSection
          title="Activer le regroupement d'amendements (allotissement)"
          description="Groupe automatiquement les amendements similaires pour faciliter le traitement"
          enabled={processingConfig.allotments.enabled}
          onEnabledChange={handleAllotmentsEnabledChange}
          disabled={disabled || isProcessing}
        >
          <ColumnSimilarityConfig
            columnHint="Choisissez la colonne utilisée pour comparer la similarité des amendements"
            columnOptions={columnOptions}
            selectedColumn={processingConfig.allotments.column}
            onColumnChange={handleAllotmentsColumnChange}
            columnError={allotmentsColumnError || undefined}
            thresholdHint="Amendements considérés comme similaires au-dessus de ce seuil (0.999 = quasi-identiques)"
            thresholdValue={processingConfig.allotments.similarity_threshold}
            onThresholdChange={handleSimilarityThresholdChange}
            thresholdError={similarityThresholdError || undefined}
            disabled={disabled || isProcessing}
          />
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
          <ColumnSimilarityConfig
            columnHint="Colonne utilisée pour la comparaison des similarités intra-lecture"
            columnOptions={columnOptions}
            selectedColumn={processingConfig.similaritiesWithinLectures.column}
            onColumnChange={handleSimilaritiesWithinLecturesColumnChange}
            columnError={similaritiesWithinLecturesColumnError || undefined}
            thresholdHint="Seuil de similarité pour les amendements intra-lecture"
            thresholdValue={
              processingConfig.similaritiesWithinLectures.similarity_threshold
            }
            onThresholdChange={handleSimilaritiesWithinLecturesThresholdChange}
            thresholdError={
              similaritiesWithinLecturesThresholdError || undefined
            }
            disabled={disabled || isProcessing}
          />
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
          <ProjectSelectionConfig
            label="Type de projet"
            hint="Sélectionnez le type de projet pour l'attribution"
            projectOptions={projectOptions}
            selectedProject={processingConfig.attribution.project_name}
            onProjectChange={handleAttributionProjectChange}
            disabled={disabled || isProcessing}
          />

          {/* should_overwrite toggle for attribution */}
          <SimpleToggleConfig
            label="Écraser les valeurs existantes"
            description="Si activé, remplace les valeurs déjà présentes; si désactivé, préserve les valeurs existantes"
            checked={processingConfig.attribution.should_overwrite}
            onChange={handleAttributionShouldOverwriteChange}
            disabled={disabled || isProcessing}
          />
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
