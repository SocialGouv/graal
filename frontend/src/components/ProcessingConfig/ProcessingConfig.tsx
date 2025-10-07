import React, { useCallback, useMemo } from "react";
import { Input } from "@codegouvfr/react-dsfr/Input";
import { fr } from "@codegouvfr/react-dsfr";
import { useProcessingStore } from "../../stores/processingStore";
import { useValidation } from "../../hooks/useValidation";
import {
  FeatureConfigSection,
  ColumnSimilarityConfig,
  ProjectSelectionConfig,
  type ColumnOption,
  type ProjectOption,
} from "../FeatureConfig";

interface ProcessingConfigProps {
  disabled?: boolean;
}

export const ProcessingConfig: React.FC<ProcessingConfigProps> = ({
  disabled = false,
}) => {
  const { processingConfig, setProcessingConfig, processingStatus } =
    useProcessingStore();
  const isProcessing =
    processingStatus !== "idle" && processingStatus !== "failed";

  // Use shared validation hook
  const {
    getOriginProjectError,
    getAllotmentsColumnError,
    getSimilarityThresholdError,
  } = useValidation();

  const handleOriginProjectChange = useCallback(
    (value: string) => {
      setProcessingConfig({
        ...processingConfig,
        originProject: value,
      });
    },
    [setProcessingConfig, processingConfig]
  );

  // Allotments handlers
  const handleAllotmentsEnabledChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        allotments: {
          ...processingConfig.allotments,
          enabled: checked,
        },
      });
    },
    [setProcessingConfig, processingConfig]
  );

  const handleAllotmentsColumnChange = useCallback(
    (value: string) => {
      setProcessingConfig({
        ...processingConfig,
        allotments: {
          ...processingConfig.allotments,
          column: value as "Corps amdt" | "Exposé amdt",
        },
      });
    },
    [setProcessingConfig, processingConfig]
  );

  const handleSimilarityThresholdChange = useCallback(
    (value: number) => {
      setProcessingConfig({
        ...processingConfig,
        allotments: {
          ...processingConfig.allotments,
          similarity_threshold: value,
        },
      });
    },
    [setProcessingConfig, processingConfig]
  );

  const originProjectError = useMemo(
    () =>
      processingConfig.originProject
        ? getOriginProjectError(processingConfig.originProject)
        : null,
    [processingConfig.originProject, getOriginProjectError]
  );

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
      getAllotmentsColumnError,
    ]
  );

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
      getSimilarityThresholdError,
    ]
  );

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
      getAllotmentsColumnError,
    ]
  );
  const similaritiesWithinLecturesThresholdError = useMemo(
    () =>
      getSimilarityThresholdError(
        processingConfig.similaritiesWithinLectures.similarity_threshold,
        processingConfig.similaritiesWithinLectures.enabled
      ),
    [
      processingConfig.similaritiesWithinLectures.similarity_threshold,
      processingConfig.similaritiesWithinLectures.enabled,
      getSimilarityThresholdError,
    ]
  );

  // Column options for dropdown
  const columnOptions: ColumnOption[] = useMemo(
    () => [
      { label: "Corps amdt", value: "Corps amdt" },
      { label: "Exposé amdt", value: "Exposé amdt" },
    ],
    []
  );

  // Project options for attribution
  const projectOptions: ProjectOption[] = useMemo(
    () => [
      { label: "PLF (Projet de Loi de Finances)", value: "PLF" },
      {
        label: "PLFSS (Projet de Loi de Financement de la Sécurité Sociale)",
        value: "PLFSS",
      },
    ],
    []
  );

  // Additional handlers for new features
  const handleSimilaritiesWithinLecturesEnabledChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        similaritiesWithinLectures: {
          ...processingConfig.similaritiesWithinLectures,
          enabled: checked,
        },
      });
    },
    [setProcessingConfig, processingConfig]
  );

  const handleAttributionEnabledChange = useCallback(
    (checked: boolean) => {
      setProcessingConfig({
        ...processingConfig,
        attribution: {
          ...processingConfig.attribution,
          enabled: checked,
        },
      });
    },
    [setProcessingConfig, processingConfig]
  );

  const handleAttributionProjectChange = useCallback(
    (value: string) => {
      setProcessingConfig({
        ...processingConfig,
        attribution: {
          ...processingConfig.attribution,
          project_name: value,
        },
      });
    },
    [setProcessingConfig, processingConfig]
  );
  const handleSimilaritiesWithinLecturesColumnChange = useCallback(
    (value: string) => {
      setProcessingConfig({
        ...processingConfig,
        similaritiesWithinLectures: {
          ...processingConfig.similaritiesWithinLectures,
          column: value as "Corps amdt" | "Exposé amdt",
        },
      });
    },
    [setProcessingConfig, processingConfig]
  );
  const handleSimilaritiesWithinLecturesThresholdChange = useCallback(
    (value: number) => {
      setProcessingConfig({
        ...processingConfig,
        similaritiesWithinLectures: {
          ...processingConfig.similaritiesWithinLectures,
          similarity_threshold: value,
        },
      });
    },
    [setProcessingConfig, processingConfig]
  );

  return (
    <div className={fr.cx("fr-mb-4w")}>
      <h3 className={fr.cx("fr-h6", "fr-mb-2w")}>
        Configuration du traitement
      </h3>

      <div className={fr.cx("fr-grid-row", "fr-grid-row--gutters")}>
        <div className={fr.cx("fr-col-12", "fr-col-md-6")}>
          <Input
            label="Projet d'origine"
            hintText="Nom du projet législatif (ex: PLFSS 2025, PLF 2024)"
            state={originProjectError ? "error" : "default"}
            stateRelatedMessage={originProjectError || undefined}
            nativeInputProps={{
              placeholder: "Ex: PLFSS 2025",
              value: processingConfig.originProject || "",
              onChange: (e) => handleOriginProjectChange(e.target.value),
              disabled: disabled || isProcessing,
              maxLength: 100,
            }}
          />
        </div>
      </div>

      {/* Allotments Configuration Section */}
      <div className={fr.cx("fr-mt-4w")}>
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
            thresholdHint="Amendements considérés comme similaires au-dessus de ce seuil (0.9999 = quasi-identiques)"
            thresholdValue={processingConfig.allotments.similarity_threshold}
            onThresholdChange={handleSimilarityThresholdChange}
            thresholdError={similarityThresholdError || undefined}
            disabled={disabled || isProcessing}
          />
        </FeatureConfigSection>
      </div>

      {/* Similarities Within Lectures Configuration Section */}
      <div className={fr.cx("fr-mt-4w")}>
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
      <div className={fr.cx("fr-mt-4w")}>
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
        </FeatureConfigSection>
      </div>
    </div>
  );
};

export default ProcessingConfig;
