import React, { useCallback, useMemo } from 'react';
import { Input } from '@codegouvfr/react-dsfr/Input';
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
  const { getOriginProjectError } = useValidation();

  const handleOriginProjectChange = useCallback((value: string) => {
    setProcessingConfig({
      ...processingConfig,
      originProject: value,
    });
  }, [setProcessingConfig, processingConfig]);

  const originProjectError = useMemo(
    () => processingConfig.originProject ? getOriginProjectError(processingConfig.originProject) : null,
    [processingConfig.originProject, getOriginProjectError]
  );

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

        {/* Future configuration fields will be added here */}
        {/* Example:
        <div className={fr.cx('fr-col-12', 'fr-col-md-6')}>
          <Input
            label="Date de traitement"
            hintText="Date personnalisée pour le traitement (optionnel)"
            nativeInputProps={{
              type: 'date',
              value: processingConfig.processingDate || '',
              onChange: (e) => handleProcessingDateChange(e.target.value),
              disabled: disabled || isProcessing,
            }}
          />
        </div>
        */}
      </div>
    </div>
  );
};

export default ProcessingConfig;
