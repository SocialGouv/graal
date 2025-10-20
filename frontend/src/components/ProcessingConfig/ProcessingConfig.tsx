import React, { useCallback, useMemo } from 'react'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Select } from '@codegouvfr/react-dsfr/Select'
import { Accordion } from '@codegouvfr/react-dsfr/Accordion'
import { fr } from '@codegouvfr/react-dsfr'
import { useQuery } from '@tanstack/react-query'
import { useProcessingStore } from '../../stores/processingStore'
import { useValidation } from '../../hooks/useValidation'
import { apiService } from '../../services/api'
import {
  FeatureConfigSection,
  ProjectSelectionConfig,
  ColumnsToCopyConfig,
  SimpleToggleConfig,
  type ColumnOption,
  type AttributionProjectOption
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

  const handleSimilaritySearchDatabaseChange = useCallback(
    (value: string) => {
      setProcessingConfig({
        ...processingConfig,
        similaritySearch: {
          ...processingConfig.similaritySearch,
          databaseFile: value || null
        }
      })
    },
    [setProcessingConfig, processingConfig]
  )

  // Fetch available databases
  const { data: databasesData, isLoading: isLoadingDatabases } = useQuery({
    queryKey: ['databases'],
    queryFn: () => apiService.listDatabases(),
    staleTime: 30000 // 30 seconds
  })

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

  return (
    <div className={fr.cx('fr-mb-4w')}>
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

      {/* Similarity Search Configuration Section */}
      <div className={fr.cx('fr-mt-4w')}>
        <FeatureConfigSection
          title="Recherche de similarités historiques"
          description="Trouve les amendements similaires dans les projets précédents"
          enabled={processingConfig.similaritySearch.enabled}
          onEnabledChange={handleSimilaritySearchEnabledChange}
          disabled={disabled || isProcessing}
        >
          {/* Database Selector */}
          <div className={fr.cx('fr-mb-4w')}>
            <DatabaseSelectorConfig
              value={processingConfig.similaritySearch.databaseFile}
              onChange={handleSimilaritySearchDatabaseFileChange}
              disabled={disabled || isProcessing}
            />
          </div>

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

          {/* Database Selector */}
          <div
            className={fr.cx('fr-grid-row', 'fr-grid-row--gutters', 'fr-mb-4w')}
          >
            <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
              <Select
                label="Base de données de similarité (optionnel)"
                hint="Sélectionnez une base pré-construite pour la recherche de similarités"
                disabled={disabled || isProcessing || isLoadingDatabases}
                nativeSelectProps={{
                  value: processingConfig.similaritySearch.databaseFile || '',
                  onChange: (e) =>
                    handleSimilaritySearchDatabaseChange(e.target.value)
                }}
              >
                <option value="">Aucune (recherche standard)</option>
                {databasesData?.databases.map((db) => (
                  <option key={db.name} value={db.name}>
                    {db.name}
                  </option>
                ))}
              </Select>
            </div>
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
