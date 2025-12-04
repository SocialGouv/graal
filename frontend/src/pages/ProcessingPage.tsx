import { fr } from '@codegouvfr/react-dsfr'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Stepper } from '@codegouvfr/react-dsfr/Stepper'
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ConfigFileSelector } from '../components/ConfigFileSelector'
import { ConfigurationManager } from '../components/ConfigurationManager/ConfigurationManager'
import DownloadButton from '../components/DownloadButton/DownloadButton'
import FileUpload from '../components/FileUpload/FileUpload'
import ProcessingConfig from '../components/ProcessingConfig/ProcessingConfig'
import ProcessingStatus from '../components/ProcessingStatus/ProcessingStatus'
import ResultsTable from '../components/ResultsTable/ResultsTable'
import {
  useDownloadExcelResults,
  useDownloadResults,
  useJobStatus,
  useResultsPreview,
  useUploadFile
} from '../hooks/useApi'
import { useValidation } from '../hooks/useValidation'
import {
  useProcessingStore,
  type ProcessingConfig as ProcessingConfigType
} from '../stores/processingStore'

export const ProcessingPage = () => {
  const navigate = useNavigate()
  const {
    jobId,
    currentStep,
    processingStatus,
    processingConfig,
    uploadedFile,
    selectedConfigFile,
    setCurrentStep,
    setUploadedFile,
    setProcessingConfig,
    setSelectedConfigFile,
    reset
  } = useProcessingStore()

  // API hooks
  const uploadFileMutation = useUploadFile()
  const downloadResultsMutation = useDownloadResults()
  const downloadExcelResultsMutation = useDownloadExcelResults()

  // Validation hook
  const { isAnyFeatureEnabled } = useValidation()

  // Job status polling - only when we have a jobId and processing
  useJobStatus(
    jobId,
    !!jobId && ['queued', 'running'].includes(processingStatus)
  )

  // Results preview - only when job is completed
  useResultsPreview(jobId, processingStatus === 'completed')

  const handleFileSelect = (file: File) => {
    setUploadedFile(file)
  }

  // Simplified validation: only require file, config, and at least one feature enabled
  const isFormValid = useMemo(
    () =>
      !!uploadedFile &&
      !!selectedConfigFile &&
      isAnyFeatureEnabled(processingConfig),
    [uploadedFile, selectedConfigFile, processingConfig, isAnyFeatureEnabled]
  )

  const handleStartProcessing = () => {
    if (!uploadedFile || !selectedConfigFile || !isFormValid) return

    // Helper function to build feature configuration conditionally
    const buildConfigIfEnabled = (enabled: boolean, config: object = {}) => {
      return enabled ? { enabled: true, ...config } : { enabled: false }
    }

    const processingRequest = {
      config_file: selectedConfigFile,
      processing_config: {
        allotment: buildConfigIfEnabled(processingConfig.allotments.enabled, {
          column: processingConfig.allotments.column,
          similarity_threshold: processingConfig.allotments.similarity_threshold
        }),
        similarities_within_lectures: buildConfigIfEnabled(
          processingConfig.similaritiesWithinLectures.enabled,
          {
            column: processingConfig.similaritiesWithinLectures.column,
            similarity_threshold:
              processingConfig.similaritiesWithinLectures.similarity_threshold
          }
        ),
        similarity_search: buildConfigIfEnabled(
          processingConfig.similaritySearch.enabled,
          {
            database_file: processingConfig.similaritySearch.databaseFile,
            origin_project: processingConfig.similaritySearch.originProject,
            clustering_similarity_thresholds:
              processingConfig.similaritySearch.clusteringSimilarityThresholds,
            fuzzy_match_similarity_thresholds:
              processingConfig.similaritySearch.fuzzyMatchSimilarityThresholds,
            similarity_threshold_overrides:
              processingConfig.similaritySearch.similarityThresholdOverrides,
            columns_to_copy: Object.fromEntries(
              Object.entries(
                processingConfig.similaritySearch.columnsToCopy
              ).map(([key, value]) => [
                key,
                {
                  enabled: value.enabled,
                  ...(value.condition && { condition: value.condition })
                }
              ])
            ),
            should_overwrite: processingConfig.similaritySearch.should_overwrite
          }
        ),
        attribution: buildConfigIfEnabled(
          processingConfig.attribution.enabled,
          {
            project_name: processingConfig.attribution.project_name,
            should_overwrite: processingConfig.attribution.should_overwrite
          }
        ),
        default_opinion: buildConfigIfEnabled(
          processingConfig.defaultOpinion.enabled,
          {
            should_overwrite: processingConfig.defaultOpinion.should_overwrite
          }
        ),
        summary_generation: buildConfigIfEnabled(
          processingConfig.summaryGeneration.enabled,
          {
            should_overwrite:
              processingConfig.summaryGeneration.should_overwrite,
            llm_type: processingConfig.summaryGeneration.llm_type,
            llm_credentials: processingConfig.summaryGeneration.llm_credentials
          }
        ),
        // Processing options at top level
        placeholder_amdt_body: processingConfig.placeholder_amdt_body
      }
    }
    uploadFileMutation.mutate({
      file: uploadedFile,
      processingRequest
    })
  }

  const handleDownloadCsv = () => {
    if (jobId) {
      downloadResultsMutation.mutate(jobId)
    }
  }

  const handleDownloadExcel = () => {
    if (jobId) {
      downloadExcelResultsMutation.mutate(jobId)
    }
  }

  const handleReset = () => {
    reset()
    navigate('/')
  }

  const handleConfigurationLoad = (
    config: ProcessingConfigType,
    configFile: string
  ) => {
    setProcessingConfig(config)
    setSelectedConfigFile(configFile)
  }

  const showResults = processingStatus === 'completed'
  const showProcessing =
    processingStatus !== 'idle' && processingStatus !== 'completed'
  const hasError =
    processingStatus === 'failed' || processingStatus === 'timeout'

  // Step titles and configuration
  const steps = [
    {
      title: 'Sélection de la configuration',
      nextTitle: 'Configuration du traitement'
    },
    { title: 'Configuration du traitement', nextTitle: 'Upload et lancement' },
    { title: 'Upload et lancement', nextTitle: 'Traitement' },
    { title: 'Traitement', nextTitle: undefined }
  ]

  const currentStepConfig = steps[currentStep - 1]

  const renderProcessingSummary = () => {
    const allot = processingConfig.allotments
    const swl = processingConfig.similaritiesWithinLectures
    const ss = processingConfig.similaritySearch
    const attr = processingConfig.attribution
    const defOp = processingConfig.defaultOpinion
    const sum = processingConfig.summaryGeneration

    type OriginProject = { name?: string } | string | null | undefined
    const origin = ss?.originProject as OriginProject
    const originProject =
      typeof origin === 'string'
        ? origin
        : origin && typeof origin === 'object' && 'name' in origin
          ? (origin.name ?? 'défini')
          : ''

    return (
      <section
        className={fr.cx('fr-mb-4w')}
        aria-labelledby="processing-summary-title"
      >
        <h2
          id="processing-summary-title"
          className={fr.cx('fr-h5', 'fr-mb-1w')}
        >
          Résumé du traitement
        </h2>
        <div className={fr.cx('fr-text--sm')}>
          <ul className={fr.cx('fr-list', 'fr-mb-0')}>
            {selectedConfigFile && (
              <li>
                <strong>Fichier de configuration :</strong> {selectedConfigFile}
              </li>
            )}
            {uploadedFile && (
              <li>
                <strong>Fichier source :</strong> {uploadedFile.name}
              </li>
            )}
            <li>
              <strong>Fonctionnalités activées :</strong>
              <ul className={fr.cx('fr-list', 'fr-mt-1w')}>
                {allot?.enabled && (
                  <li>
                    Allotissement
                    {allot?.column ? ` — colonne: ${allot.column}` : ''}
                    {typeof allot?.similarity_threshold === 'number'
                      ? `, seuil: ${allot.similarity_threshold}`
                      : ''}
                  </li>
                )}
                {swl?.enabled && (
                  <li>
                    Similarités intra-séance
                    {swl?.column ? ` — colonne: ${swl.column}` : ''}
                    {typeof swl?.similarity_threshold === 'number'
                      ? `, seuil: ${swl.similarity_threshold}`
                      : ''}
                  </li>
                )}
                {ss?.enabled && (
                  <li>
                    Recherche de similarités
                    {ss?.databaseFile ? ` — base: ${ss.databaseFile}` : ''}
                    {originProject ? `, origine: ${originProject}` : ''}
                  </li>
                )}
                {attr?.enabled && <li>Attribution</li>}
                {defOp?.enabled && <li>Opinion par défaut</li>}
                {sum?.enabled && (
                  <li>
                    Génération de résumés — LLM: {sum.llm_type || 'Non défini'}
                  </li>
                )}
                {!allot?.enabled &&
                  !swl?.enabled &&
                  !ss?.enabled &&
                  !attr?.enabled &&
                  !defOp?.enabled &&
                  !sum?.enabled && <li>Aucune</li>}
              </ul>
            </li>
          </ul>
        </div>
      </section>
    )
  }

  return (
    <div className={fr.cx('fr-container', 'fr-py-6w')}>
      <main>
        {/* Back to Home Button */}
        {!showProcessing && !showResults && (
          <div className={fr.cx('fr-mb-4w')}>
            <Button
              priority="tertiary no outline"
              iconId="fr-icon-arrow-left-line"
              iconPosition="left"
              onClick={() => navigate('/')}
              size="small"
            >
              Retour à l'accueil
            </Button>
          </div>
        )}

        {/* Results Header with Reset Button */}
        {showResults && (
          <div
            className={fr.cx('fr-grid-row', 'fr-grid-row--gutters', 'fr-mb-4w')}
          >
            <div className={fr.cx('fr-col-12', 'fr-col-md-8')}>
              <h1 className={fr.cx('fr-mb-0')}>Résultats du traitement</h1>
            </div>
            <div className={fr.cx('fr-col-12', 'fr-col-md-4')}>
              <div style={{ textAlign: 'right' }}>
                <Button
                  priority="secondary"
                  size="small"
                  onClick={handleReset}
                  iconId="fr-icon-refresh-line"
                  iconPosition="left"
                >
                  Nouveau traitement
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Stepper - show when not showing results (also during processing) */}
        {!showResults && (
          <div className={fr.cx('fr-mb-6w')}>
            <Stepper
              currentStep={showProcessing ? 4 : currentStep}
              stepCount={4}
              title={showProcessing ? 'Traitement' : currentStepConfig.title}
              nextTitle={
                showProcessing ? undefined : currentStepConfig.nextTitle
              }
            />
          </div>
        )}

        {/* Configuration and File Upload Section */}
        {!showResults && !showProcessing && (
          <>
            {/* Step 1: Configuration */}
            {currentStep === 1 && (
              <section className={fr.cx('fr-mb-6w')}>
                <ConfigFileSelector disabled={uploadFileMutation.isPending} />
                <div
                  className={fr.cx('fr-mt-4w')}
                  style={{ textAlign: 'right' }}
                >
                  <Button
                    priority="primary"
                    onClick={() => setCurrentStep(2)}
                    disabled={!selectedConfigFile}
                    iconId="fr-icon-arrow-right-line"
                    iconPosition="right"
                  >
                    Continuer
                  </Button>
                </div>
              </section>
            )}

            {/* Step 2: Processing Configuration */}
            {currentStep === 2 && (
              <section className={fr.cx('fr-mb-6w')}>
                <ConfigurationManager
                  currentConfig={processingConfig}
                  selectedConfigFile={selectedConfigFile}
                  onConfigurationLoad={handleConfigurationLoad}
                />
                <ProcessingConfig disabled={uploadFileMutation.isPending} />
                <div
                  className={fr.cx('fr-mt-4w')}
                  style={{ display: 'flex', justifyContent: 'space-between' }}
                >
                  <Button
                    priority="secondary"
                    onClick={() => setCurrentStep(1)}
                    iconId="fr-icon-arrow-left-line"
                    iconPosition="left"
                  >
                    Retour
                  </Button>
                  <Button
                    priority="primary"
                    onClick={() => setCurrentStep(3)}
                    disabled={
                      !isAnyFeatureEnabled(processingConfig) ||
                      (processingConfig.summaryGeneration.enabled &&
                        !processingConfig.summaryGeneration.llm_type)
                    }
                    iconId="fr-icon-arrow-right-line"
                    iconPosition="right"
                  >
                    Continuer
                  </Button>
                </div>
              </section>
            )}

            {/* Step 3: File Upload */}
            {currentStep === 3 && (
              <section className={fr.cx('fr-mb-6w')}>
                <FileUpload
                  onFileSelect={handleFileSelect}
                  onStartProcessing={handleStartProcessing}
                  disabled={uploadFileMutation.isPending}
                  isFormValid={!!isFormValid}
                />
                <div
                  className={fr.cx(
                    'fr-grid-row',
                    'fr-grid-row--gutters',
                    'fr-mt-4w'
                  )}
                >
                  <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
                    <Button
                      priority="secondary"
                      onClick={() => setCurrentStep(2)}
                      disabled={uploadFileMutation.isPending}
                      iconId="fr-icon-arrow-left-line"
                      iconPosition="left"
                    >
                      Retour
                    </Button>
                  </div>
                  <div
                    className={fr.cx('fr-col-12', 'fr-col-md-6')}
                    style={{ textAlign: 'right' }}
                  >
                    <Button
                      priority="primary"
                      size="large"
                      onClick={handleStartProcessing}
                      disabled={!isFormValid || uploadFileMutation.isPending}
                      iconId="fr-icon-play-fill"
                      iconPosition="left"
                    >
                      Commencer le traitement
                    </Button>
                  </div>
                </div>
              </section>
            )}
          </>
        )}

        {/* Processing Status Section */}
        {showProcessing && (
          <>
            {renderProcessingSummary()}
            <ProcessingStatus />
            {hasError && (
              <div className={fr.cx('fr-mt-2w')} style={{ textAlign: 'right' }}>
                <Button
                  priority="secondary"
                  size="small"
                  onClick={() => setCurrentStep(2)}
                  iconId="fr-icon-arrow-left-line"
                  iconPosition="left"
                >
                  Retour à la configuration
                </Button>
              </div>
            )}
          </>
        )}

        {/* Results Section */}
        {showResults && (
          <>
            {renderProcessingSummary()}
            <DownloadButton
              onDownloadCsv={handleDownloadCsv}
              onDownloadExcel={handleDownloadExcel}
              isCsvLoading={downloadResultsMutation.isPending}
              isExcelLoading={downloadExcelResultsMutation.isPending}
            />
            <ResultsTable />
          </>
        )}
      </main>
    </div>
  )
}
