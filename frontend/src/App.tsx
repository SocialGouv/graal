import React, { useMemo } from 'react'
import { Header } from '@codegouvfr/react-dsfr/Header'
import { Footer } from '@codegouvfr/react-dsfr/Footer'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { fr } from '@codegouvfr/react-dsfr'

// Import components and providers
import QueryProvider from './providers/QueryProvider'
import ProcessingConfig from './components/ProcessingConfig/ProcessingConfig'
import FileUpload from './components/FileUpload/FileUpload'
import ProcessingStatus from './components/ProcessingStatus/ProcessingStatus'
import ResultsTable from './components/ResultsTable/ResultsTable'
import DownloadButton from './components/DownloadButton/DownloadButton'

// Import hooks and store
import { useProcessingStore } from './stores/processingStore'
import {
  useUploadFile,
  useJobStatus,
  useResultsPreview,
  useDownloadResults,
  useDownloadExcelResults
} from './hooks/useApi'
import { useValidation } from './hooks/useValidation'

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
  const {
    jobId,
    processingStatus,
    processingConfig,
    uploadedFile,
    setUploadedFile,
    reset
  } = useProcessingStore()

  // API hooks
  const uploadFileMutation = useUploadFile()
  const downloadResultsMutation = useDownloadResults()
  const downloadExcelResultsMutation = useDownloadExcelResults()

  // Validation hook
  const { isOriginProjectValid } = useValidation()

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
      (!processingConfig.similaritySearch.enabled ||
        isOriginProjectValid(processingConfig.similaritySearch.originProject)),
    [
      uploadedFile,
      processingConfig.similaritySearch.enabled,
      processingConfig.similaritySearch.originProject,
      isOriginProjectValid
    ]
  )

  const handleStartProcessing = () => {
    if (!uploadedFile || !isFormValid) return

    // Helper function to build feature configuration conditionally
    const buildConfigIfEnabled = (enabled: boolean, config: object = {}) => {
      return enabled ? { enabled: true, ...config } : { enabled: false }
    }

    const processingRequest = {
      processing_config: {
        allotments: buildConfigIfEnabled(processingConfig.allotments.enabled, {
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
            )
          }
        ),
        attribution: buildConfigIfEnabled(
          processingConfig.attribution.enabled,
          {
            project_name: processingConfig.attribution.project_name
          }
        ),
        default_opinion: buildConfigIfEnabled(
          processingConfig.defaultOpinion.enabled
        )
      }
    }
    uploadFileMutation.mutate({ file: uploadedFile, processingRequest })
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
          <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
            <div className={fr.cx('fr-col-12', 'fr-col-md-8')}>
              <h1>Traitement automatisé des amendements</h1>
              <p className={fr.cx('fr-text--lead')}>
                GRAAL permet de traiter et analyser les amendements législatifs
                pour faciliter le travail des agents gouvernementaux.
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
                <ProcessingConfig disabled={uploadFileMutation.isPending} />
                <FileUpload
                  onFileSelect={handleFileSelect}
                  onStartProcessing={handleStartProcessing}
                  disabled={uploadFileMutation.isPending}
                  isFormValid={!!isFormValid}
                />
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
