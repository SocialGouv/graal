import React from 'react';
import { Button } from '@codegouvfr/react-dsfr/Button';
import { fr } from '@codegouvfr/react-dsfr';
import { useProcessingStore } from '../../stores/processingStore';

interface DownloadButtonProps {
  onDownload: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  className?: string;
}

export const DownloadButton: React.FC<DownloadButtonProps> = ({
  onDownload,
  isLoading = false,
  disabled = false,
  className,
}) => {
  const { processingStatus, jobId, totalRows } = useProcessingStore();

  const isDownloadAvailable = processingStatus === 'completed' && jobId && totalRows > 0;
  const isButtonDisabled = disabled || !isDownloadAvailable || isLoading;

  if (!isDownloadAvailable) {
    return null;
  }

  return (
    <div className={`${fr.cx('fr-mb-4w')} ${className || ''}`}>
      <div className={fr.cx('fr-mb-2w')}>
        <h3 className={fr.cx('fr-h6')}>Télécharger les résultats</h3>
        <p className={fr.cx('fr-text--sm')}>
          Téléchargez le fichier CSV complet contenant tous les {totalRows} amendements traités.
        </p>
      </div>

      <Button
        priority="primary"
        iconId="fr-icon-download-line"
        iconPosition="left"
        onClick={onDownload}
        disabled={isButtonDisabled}
        className={fr.cx('fr-btn--icon-left')}
      >
        {isLoading ? 'Téléchargement...' : 'Télécharger le CSV complet'}
      </Button>

      <div className={fr.cx('fr-mt-2w', 'fr-text--sm')}>
        <p>
          Le fichier CSV contient toutes les colonnes et tous les amendements traités par GRAAL.
        </p>
      </div>
    </div>
  );
};

export default DownloadButton;
