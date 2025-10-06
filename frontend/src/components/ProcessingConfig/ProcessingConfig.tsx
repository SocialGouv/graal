import React, { useCallback, useMemo } from 'react';
import { Input } from '@codegouvfr/react-dsfr/Input';
import { Checkbox } from '@codegouvfr/react-dsfr/Checkbox';
import { Select } from '@codegouvfr/react-dsfr/Select';
import { Range } from '@codegouvfr/react-dsfr/Range';
import { Accordion } from '@codegouvfr/react-dsfr/Accordion';
import { fr } from '@codegouvfr/react-dsfr';
import { useProcessingStore } from '../../stores/processingStore';
import { useValidation } from '../../hooks/useValidation';

interface ProcessingConfigProps {
  disabled?: boolean;
}

export const ProcessingConfig: React.FC<ProcessingConfigProps> = ({ disabled = false }) => {
  const { processingConfig, setProcessingConfig, processingStatus } = useProcessingStore();
  const isProcessing = processingStatus !== 'idle' && processingStatus !== 'failed';

  // Use shared validation hook
  const { getOriginProjectError, getAllotmentsColumnError, getSimilarityThresholdError } = useValidation();

  const handleOriginProjectChange = useCallback((value: string) => {
    setProcessingConfig({
      ...processingConfig,
      originProject: value,
    });
  }, [setProcessingConfig, processingConfig]);

  // Allotments handlers
  const handleAllotmentsEnabledChange = useCallback((checked: boolean) => {
    setProcessingConfig({
      ...processingConfig,
      allotments: {
        ...processingConfig.allotments,
        enabled: checked,
      },
    });
  }, [setProcessingConfig, processingConfig]);

  const handleAllotmentsColumnChange = useCallback((value: string) => {
    setProcessingConfig({
      ...processingConfig,
      allotments: {
        ...processingConfig.allotments,
        column: value as 'Corps amdt' | 'Exposé amdt' | 'Corps amdt original',
      },
    });
  }, [setProcessingConfig, processingConfig]);

  const handleSimilarityThresholdChange = useCallback((value: number) => {
    setProcessingConfig({
      ...processingConfig,
      allotments: {
        ...processingConfig.allotments,
        similarity_threshold: value,
      },
    });
  }, [setProcessingConfig, processingConfig]);

  const originProjectError = useMemo(
    () => processingConfig.originProject ? getOriginProjectError(processingConfig.originProject) : null,
    [processingConfig.originProject, getOriginProjectError]
  );

  // Allotments validation
  const allotmentsColumnError = useMemo(
    () => getAllotmentsColumnError(processingConfig.allotments.column, processingConfig.allotments.enabled),
    [processingConfig.allotments.column, processingConfig.allotments.enabled, getAllotmentsColumnError]
  );

  const similarityThresholdError = useMemo(
    () => getSimilarityThresholdError(processingConfig.allotments.similarity_threshold, processingConfig.allotments.enabled),
    [processingConfig.allotments.similarity_threshold, processingConfig.allotments.enabled, getSimilarityThresholdError]
  );

  // Column options for dropdown
  const columnOptions = useMemo(() => [
    { label: 'Corps amdt', value: 'Corps amdt' },
    { label: 'Exposé amdt', value: 'Exposé amdt' },
  ], []);

  return (
    <div className={fr.cx('fr-mb-4w')}>
      <h3 className={fr.cx('fr-h6', 'fr-mb-2w')}>Configuration du traitement</h3>

      <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
        <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
          <Input
            label="Projet d'origine"
            hintText="Nom du projet législatif (ex: PLFSS 2025, PLF 2024)"
            state={originProjectError ? 'error' : 'default'}
            stateRelatedMessage={originProjectError || undefined}
            nativeInputProps={{
              placeholder: 'Ex: PLFSS 2025',
              value: processingConfig.originProject || '',
              onChange: (e) => handleOriginProjectChange(e.target.value),
              disabled: disabled || isProcessing,
              maxLength: 100,
            }}
          />
        </div>

      </div>

      {/* Allotments Configuration Section */}
      <div className={fr.cx('fr-mt-4w')}>
        {!processingConfig.allotments.enabled ? (
          <div className={fr.cx('fr-p-2w')} style={{ border: '1px solid #ddd', borderRadius: '4px' }}>
            <Checkbox
              options={[
                {
                  label: "Activer le regroupement d'amendements (allotissement)",
                  hintText: "Groupe automatiquement les amendements similaires pour faciliter le traitement",
                  nativeInputProps: {
                    checked: processingConfig.allotments.enabled,
                    onChange: (e) => handleAllotmentsEnabledChange(e.target.checked),
                    disabled: disabled || isProcessing,
                  },
                },
              ]}
            />
          </div>
        ) : (
          <Accordion
            label={
              <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters', 'fr-grid-row--middle')}>
                <div className={fr.cx('fr-col')}>
                  <Checkbox
                    options={[
                      {
                        label: "Activer le regroupement d'amendements (allotissement)",
                        hintText: "Groupe automatiquement les amendements similaires pour faciliter le traitement",
                        nativeInputProps: {
                          checked: processingConfig.allotments.enabled,
                          onChange: (e) => handleAllotmentsEnabledChange(e.target.checked),
                          disabled: disabled || isProcessing,
                        },
                      },
                    ]}
                  />
                </div>
                <div className={fr.cx('fr-col')} style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', flex: '0 0 auto' }}>
                  <span className={fr.cx('fr-text--sm', 'fr-text--bold')}>
                    Configuration avancée
                  </span>
                </div>
              </div>
            }
            defaultExpanded={false}
          >
            <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters', 'fr-mt-2w')}>
              <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
                <Select
                  label="Colonne à analyser"
                  hint="Choisissez la colonne utilisée pour comparer la similarité des amendements"
                  state={allotmentsColumnError ? 'error' : 'default'}
                  stateRelatedMessage={allotmentsColumnError || undefined}
                  nativeSelectProps={{
                    value: processingConfig.allotments.column,
                    onChange: (e) => handleAllotmentsColumnChange(e.target.value),
                    disabled: disabled || isProcessing,
                  }}
                >
                  <option value="" disabled>
                    Sélectionnez une colonne
                  </option>
                  {columnOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              </div>

              <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
                <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
                  <div className={fr.cx('fr-col-8')}>
                    <Range
                      label="Seuil de similarité"
                      hintText="Amendements considérés comme similaires au-dessus de ce seuil (0.9999 = quasi-identiques)"
                      min={0}
                      max={1}
                      step={0.0001}
                      nativeInputProps={{
                        value: processingConfig.allotments.similarity_threshold,
                        onChange: (e) => handleSimilarityThresholdChange(parseFloat(e.target.value)),
                        disabled: disabled || isProcessing,
                      }}
                    />
                  </div>
                  <div className={fr.cx('fr-col-4')}>
                    <Input
                      label="Valeur"
                      state={similarityThresholdError ? 'error' : 'default'}
                      stateRelatedMessage={similarityThresholdError || undefined}
                      nativeInputProps={{
                        type: 'number',
                        min: 0,
                        max: 1,
                        step: 0.0001,
                        value: processingConfig.allotments.similarity_threshold,
                        onChange: (e) => handleSimilarityThresholdChange(parseFloat(e.target.value) || 0),
                        disabled: disabled || isProcessing,
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </Accordion>
        )}
      </div>
    </div>
  );
};

export default ProcessingConfig;
