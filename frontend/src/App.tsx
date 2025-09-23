import React from "react";
import { Header } from "@codegouvfr/react-dsfr/Header";
import { Footer } from "@codegouvfr/react-dsfr/Footer";
import { Button } from "@codegouvfr/react-dsfr/Button";
import { fr } from "@codegouvfr/react-dsfr";

// Import components and providers
import QueryProvider from "./providers/QueryProvider";
import FileUpload from "./components/FileUpload/FileUpload";
import ProcessingStatus from "./components/ProcessingStatus/ProcessingStatus";
import ResultsTable from "./components/ResultsTable/ResultsTable";
import DownloadButton from "./components/DownloadButton/DownloadButton";

// Import hooks and store
import { useProcessingStore } from "./stores/processingStore";
import { useUploadFile, useJobStatus, useResultsPreview, useDownloadResults, useDownloadExcelResults } from "./hooks/useApi";

// Container is a simple div wrapper, we can create it ourselves or use a regular div
const Container = ({ children, ...props }: { children: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => (
  <div className={fr.cx("fr-container")} {...props}>
    {children}
  </div>
);

function AppContent() {
  const {
    jobId,
    processingStatus,
    setUploadedFile,
    reset,
  } = useProcessingStore();

  // API hooks
  const uploadFileMutation = useUploadFile();
  const downloadResultsMutation = useDownloadResults();
  const downloadExcelResultsMutation = useDownloadExcelResults();

  // Job status polling - only when we have a jobId and processing
  useJobStatus(
    jobId,
    !!jobId && ['queued', 'running'].includes(processingStatus)
  );

  // Results preview - only when job is completed
  useResultsPreview(
    jobId,
    processingStatus === 'completed'
  );

  const handleFileSelect = (file: File) => {
    setUploadedFile(file);
    uploadFileMutation.mutate(file);
  };

  const handleDownloadCsv = () => {
    if (jobId) {
      downloadResultsMutation.mutate(jobId);
    }
  };

  const handleDownloadExcel = () => {
    if (jobId) {
      downloadExcelResultsMutation.mutate(jobId);
    }
  };

  const handleReset = () => {
    reset();
  };

  const showResults = processingStatus === 'completed';
  const showProcessing = processingStatus !== 'idle';

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
          href: "/",
          title: "Accueil - GRAAL"
        }}
      />

      <Container>
        <main className={fr.cx("fr-py-6w")}>
          <div className={fr.cx("fr-grid-row", "fr-grid-row--gutters")}>
            <div className={fr.cx("fr-col-12", "fr-col-md-8")}>
              <h1>Traitement automatisé des amendements</h1>
              <p className={fr.cx("fr-text--lead")}>
                GRAAL permet de traiter et analyser les amendements législatifs pour
                faciliter le travail des agents gouvernementaux.
              </p>

              {!showProcessing && (
                <p>
                  Téléchargez un fichier JSON contenant des amendements pour commencer
                  le traitement automatisé.
                </p>
              )}
            </div>

            {showResults && (
              <div className={fr.cx("fr-col-12", "fr-col-md-4")}>
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

          <div className={fr.cx("fr-mt-4w")}>
            {/* File Upload Section */}
            {!showResults && (
              <FileUpload
                onFileSelect={handleFileSelect}
                disabled={uploadFileMutation.isPending}
              />
            )}

            {/* Processing Status Section */}
            {showProcessing && (
              <ProcessingStatus />
            )}

            {/* Results Section */}
            {showResults && (
              <>
                <ResultsTable />
                <DownloadButton
                  onDownloadCsv={handleDownloadCsv}
                  onDownloadExcel={handleDownloadExcel}
                  isCsvLoading={downloadResultsMutation.isPending}
                  isExcelLoading={downloadExcelResultsMutation.isPending}
                />
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
          href: "#",
        }}
        accessibilityLinkProps={{
          href: "#",
        }}
        termsLinkProps={{
          href: "#",
        }}
      />
    </>
  );
}

function App() {
  return (
    <QueryProvider>
      <AppContent />
    </QueryProvider>
  );
}

export default App;
