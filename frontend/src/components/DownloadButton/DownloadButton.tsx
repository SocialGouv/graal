import React from 'react';
import { ButtonsGroup } from '@codegouvfr/react-dsfr/ButtonsGroup';
import { fr } from '@codegouvfr/react-dsfr';
import { useProcessingStore } from '../../stores/processingStore';

interface DownloadButtonProps {
  onDownloadCsv: () => void;
  onDownloadExcel: () => void;
  isCsvLoading?: boolean;
  isExcelLoading?: boolean;
  disabled?: boolean;
  className?: string;
}

export const DownloadButton: React.FC<DownloadButtonProps> = ({
  onDownloadCsv,
  onDownloadExcel,
  isCsvLoading = false,
  isExcelLoading = false,
  disabled = false,
  className,
}) => {
  const { processingStatus, jobId, totalRows } = useProcessingStore();

  const isDownloadAvailable = processingStatus === 'completed' && jobId && totalRows > 0;
  const isAnyLoading = isCsvLoading || isExcelLoading;
  const areButtonsDisabled = disabled || !isDownloadAvailable || isAnyLoading;

  if (!isDownloadAvailable) {
    return null;
  }

  return (
    <div className={`${fr.cx('fr-mb-4w')} ${className || ''}`}>
      <div className={fr.cx('fr-mb-2w')}>
        <h3 className={fr.cx('fr-h6')}>Télécharger les résultats</h3>
        <p className={fr.cx('fr-text--sm')}>
          Téléchargez les résultats complets contenant les {totalRows} amendements traités par GRAAL.
        </p>
      </div>

      <ButtonsGroup
        buttonsEquisized
        inlineLayoutWhen="always"
        buttons={[
          {
            children: isCsvLoading ? 'Téléchargement...' : 'Télécharger CSV',
            iconId: 'fr-icon-download-line',
            iconPosition: 'left',
            onClick: onDownloadCsv,
            disabled: areButtonsDisabled,
            priority: 'primary',
          },
          {
            children: isExcelLoading ? 'Téléchargement...' : 'Télécharger Excel',
            iconId: 'fr-icon-download-line',
            iconPosition: 'left',
            onClick: onDownloadExcel,
            disabled: areButtonsDisabled,
            priority: 'secondary',
          },
        ]}
      />

      <div className={fr.cx('fr-mt-2w', 'fr-text--sm')}>
        <p>
          Les fichiers contiennent toutes les colonnes et tous les amendements traités par GRAAL.
          Le format Excel préserve la mise en forme et permet une meilleure manipulation des données par l'humain.
          Le CSV permet l'import dans l'outil Signale.
        </p>
      </div>
    </div>
  );
};

export default DownloadButton;
