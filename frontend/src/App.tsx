import { fr } from '@codegouvfr/react-dsfr'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Footer } from '@codegouvfr/react-dsfr/Footer'
import { Header } from '@codegouvfr/react-dsfr/Header'
import {
  SegmentedControl,
  type SegmentedControlProps
} from '@codegouvfr/react-dsfr/SegmentedControl'
import React, { useMemo, useState } from 'react'

// Import components and providers
import { Admin } from './components/Admin'
import { ConfigFileSelector } from './components/ConfigFileSelector'
import { DatabaseBuilder } from './components/DatabaseBuilder'
import DownloadButton from './components/DownloadButton/DownloadButton'
import FileUpload from './components/FileUpload/FileUpload'
import ProcessingConfig from './components/ProcessingConfig/ProcessingConfig'
import ProcessingStatus from './components/ProcessingStatus/ProcessingStatus'
import ResultsTable from './components/ResultsTable/ResultsTable'
import QueryProvider from './providers/QueryProvider'

// Import hooks and store
import {
  useDownloadExcelResults,
  useDownloadResults,
  useJobStatus,
  useResultsPreview,
  useUploadFile
} from './hooks/useApi'
import { useAuth } from './hooks/useAuth'
import { useValidation } from './hooks/useValidation'
import { useProcessingStore } from './stores/processingStore'

// Container is a simple div wrapper, we can create it ourselves or use a regular div
const Container = ({
  children,
  ...props
}: { children: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => (
  <div className={fr.cx('fr-container')} {...props}>
    {children}
  </div>
)

function AppContent() {
  const { isAdmin, isLoading, error } = useAuth()

  const [activeView, setActiveView] = useState<
    'processing' | 'database' | 'admin'
  >('processing')

  // Build segments array based on admin status
  const viewSegments = useMemo(() => {
    const baseSegments = [
      {
        label: 'Amendment Processing',
        nativeInputProps: {
          checked: activeView === 'processing',
          onChange: () => setActiveView('processing')
        }
      },
      {
        label: 'Database Builder',
        nativeInputProps: {
          checked: activeView === 'database',
          onChange: () => setActiveView('database')
        }
      }
    ]

    if (isAdmin) {
      baseSegments.push({
        label: 'Admin',
        nativeInputProps: {
          checked: activeView === 'admin',
          onChange: () => setActiveView('admin')
        }
      })
    }

    return baseSegments as unknown as SegmentedControlProps['segments']
  }, [activeView, isAdmin])

  const {
    jobId,
    processingStatus,
    processingConfig,
    uploadedFile,
    selectedConfigFile,
    setUploadedFile,
    reset
  } = useProcessingStore()

  // API hooks
  const uploadFileMutation = useUploadFile()
  const downloadResultsMutation = useDownloadResults()
  const downloadExcelResultsMutation = useDownloadExcelResults()

  // Validation hook
  const { isOriginProjectValid, isAnyFeatureEnabled } = useValidation()

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

  const isFormValid = useMemo(
    () =>
      uploadedFile &&
      selectedConfigFile &&
      isAnyFeatureEnabled(processingConfig) &&
      (!processingConfig.similaritySearch.enabled ||
        (isOriginProjectValid(
          processingConfig.similaritySearch.originProject
        ) &&
          processingConfig.similaritySearch.databaseFile !== null &&
          processingConfig.similaritySearch.databaseFile !== '')),
    [
      uploadedFile,
      selectedConfigFile,
      processingConfig,
      isAnyFeatureEnabled,
      isOriginProjectValid
    ]
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
  }

  // Show loading state
  if (isLoading) {
    return (
      <Container>
        <div className={fr.cx('fr-py-6w')}>
          <p>Chargement...</p>
        </div>
      </Container>
    )
  }

  // Show error state (optional - depends on requirements)
  if (error) {
    console.warn('Auth error:', error)
    // Show non-blocking notification
    return (
      <Container>
        <div className={fr.cx('fr-py-6w')}>
          <div className={fr.cx('fr-alert', 'fr-alert--warning')}>
            <p>
              Impossible de vérifier les permissions administrateur. Vous pouvez
              continuer avec les fonctionnalités de base.
            </p>
          </div>
        </div>
      </Container>
    )
  }

  const showResults = processingStatus === 'completed'
  const showProcessing = processingStatus !== 'idle'

  return (
    <>
      <Header
        brandTop={
          <>
            République
            <br />
            Française
          </>
        }
        serviceTitle="GRAAL"
        serviceTagline="Gestion et Répartition Automatisée des Amendements Législatifs"
        homeLinkProps={{
          href: '/',
          title: 'Accueil - GRAAL'
        }}
      />

      <Container>
        <main className={fr.cx('fr-py-6w')}>
          {/* View Selector */}
          <div className={fr.cx('fr-mb-4w')}>
            <SegmentedControl
              legend="Select view"
              hideLegend
              segments={viewSegments}
            />
          </div>

          {/* Admin View */}
          {activeView === 'admin' && isAdmin && <Admin />}

          {/* Database Builder View */}
          {activeView === 'database' && <DatabaseBuilder />}

          {/* Processing View */}
          {activeView === 'processing' && (
            <>
              <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
                <div className={fr.cx('fr-col-12', 'fr-col-md-8')}>
                  <h1>Traitement automatisé des amendements</h1>
                  <p className={fr.cx('fr-text--lead')}>
                    GRAAL permet de traiter et analyser les amendements
                    législatifs pour faciliter le travail des agents
                    gouvernementaux.
                  </p>

                  {!showProcessing && (
                    <p>
                      Téléchargez un fichier JSON contenant des amendements pour
                      commencer le traitement automatisé.
                    </p>
                  )}
                </div>

                {showResults && (
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
                )}
              </div>

              <div className={fr.cx('fr-mt-4w')}>
                {/* Configuration and File Upload Section */}
                {!showResults && (
                  <>
                    <section className={fr.cx('fr-mb-6w')}>
                      <h2 className={fr.cx('fr-h3')}>1. Configuration</h2>
                      <ConfigFileSelector
                        disabled={uploadFileMutation.isPending}
                      />
                    </section>

                    <section className={fr.cx('fr-mb-6w')}>
                      <h2 className={fr.cx('fr-h3')}>
                        2. Configuration du traitement
                      </h2>
                      <ProcessingConfig
                        disabled={uploadFileMutation.isPending}
                      />
                    </section>

                    <section className={fr.cx('fr-mb-6w')}>
                      <h2 className={fr.cx('fr-h3')}>3. Upload de fichier</h2>
                      <FileUpload
                        onFileSelect={handleFileSelect}
                        onStartProcessing={handleStartProcessing}
                        disabled={uploadFileMutation.isPending}
                        isFormValid={!!isFormValid}
                      />
                    </section>
                  </>
                )}

                {/* Processing Status Section */}
                {showProcessing && <ProcessingStatus />}

                {/* Results Section */}
                {showResults && (
                  <>
                    <DownloadButton
                      onDownloadCsv={handleDownloadCsv}
                      onDownloadExcel={handleDownloadExcel}
                      isCsvLoading={downloadResultsMutation.isPending}
                      isExcelLoading={downloadExcelResultsMutation.isPending}
                    />
                    <ResultsTable />
                  </>
                )}
              </div>
            </>
          )}
        </main>
      </Container>

      <Footer
        brandTop={
          <>
            République
            <br />
            Française
          </>
        }
        accessibility="fully compliant"
        contentDescription="Application web pour le traitement automatisé des amendements législatifs"
        websiteMapLinkProps={{
          href: '#'
        }}
        accessibilityLinkProps={{
          href: '#'
        }}
        termsLinkProps={{
          href: '#'
        }}
      />
    </>
  )
}

function App() {
  return (
    <QueryProvider>
      <AppContent />
    </QueryProvider>
  )
}

export default App
