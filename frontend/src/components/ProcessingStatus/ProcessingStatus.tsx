import React from 'react';
import { Alert } from '@codegouvfr/react-dsfr/Alert';
import { Badge } from '@codegouvfr/react-dsfr/Badge';
import { fr } from '@codegouvfr/react-dsfr';
import { useProcessingStore } from '../../stores/processingStore';

interface ProcessingStatusProps {
  className?: string;
}

export const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ className }) => {
  const {
    processingStatus,
    progressPercent,
    progressMessage,
    startedAt,
    updatedAt,
    error,
  } = useProcessingStore();

  const getStatusBadge = () => {
    switch (processingStatus) {
      case 'idle':
        return null;
      case 'uploading':
        return <Badge severity="info">Téléchargement</Badge>;
      case 'queued':
        return <Badge severity="info">En attente</Badge>;
      case 'running':
        return <Badge severity="info">En cours</Badge>;
      case 'completed':
        return <Badge severity="success">Terminé</Badge>;
      case 'failed':
        return <Badge severity="error">Échec</Badge>;
      case 'timeout':
        return <Badge severity="warning">Timeout</Badge>;
      default:
        return <Badge severity="info">{processingStatus}</Badge>;
    }
  };

  const getStatusMessage = () => {
    if (error) {
      return error;
    }

    if (progressMessage) {
      return progressMessage;
    }

    switch (processingStatus) {
      case 'idle':
        return 'Prêt à traiter un fichier';
      case 'uploading':
        return 'Téléchargement du fichier en cours...';
      case 'queued':
        return 'Fichier en attente de traitement';
      case 'running':
        return 'Traitement des amendements en cours...';
      case 'completed':
        return 'Traitement terminé avec succès';
      case 'failed':
        return 'Le traitement a échoué';
      case 'timeout':
        return 'Le traitement a pris trop de temps';
      default:
        return `Statut: ${processingStatus}`;
    }
  };

  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return null;
    try {
      const date = new Date(dateString);
      return date.toLocaleString('fr-FR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  const isProcessing = ['uploading', 'queued', 'running'].includes(processingStatus);
  const isCompleted = processingStatus === 'completed';
  const hasError = processingStatus === 'failed' || processingStatus === 'timeout' || !!error;

  if (processingStatus === 'idle') {
    return null;
  }

  return (
    <div className={`${fr.cx('fr-mb-4w')} ${className || ''}`}>
      <div className={fr.cx('fr-mb-2w')}>
        <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters', 'fr-grid-row--middle')}>
          <div className={fr.cx('fr-col')}>
            <h3 className={fr.cx('fr-h6', 'fr-mb-0')}>Statut du traitement</h3>
          </div>
          <div className={fr.cx('fr-col')}>
            {getStatusBadge()}
          </div>
        </div>
      </div>

      {isProcessing && (
        <div className={fr.cx('fr-mb-3w')}>
          <div className={fr.cx('fr-mb-1w')}>
            <label className={fr.cx('fr-text--sm', 'fr-text--bold')}>Progression</label>
          </div>
          <div
            style={{
              width: '100%',
              height: '8px',
              backgroundColor: '#e5e5e5',
              borderRadius: '4px',
              overflow: 'hidden'
            }}
          >
            <div
              style={{
                width: `${progressPercent}%`,
                height: '100%',
                backgroundColor: '#000091',
                transition: 'width 0.3s ease'
              }}
            />
          </div>
          <p className={fr.cx('fr-text--sm', 'fr-mt-1w', 'fr-mb-0')}>
            {progressPercent}% - {getStatusMessage()}
          </p>
        </div>
      )}

      {isCompleted && (
        <Alert
          severity="success"
          title="Traitement terminé"
          description={getStatusMessage()}
          className={fr.cx('fr-mb-2w')}
        />
      )}

      {hasError && (
        <Alert
          severity="error"
          title="Erreur de traitement"
          description={getStatusMessage()}
          className={fr.cx('fr-mb-2w')}
        />
      )}

      {(startedAt || updatedAt) && (
        <div className={fr.cx('fr-text--sm')} style={{ color: '#666' }}>
          {startedAt && (
            <p className={fr.cx('fr-mb-1v')}>
              <strong>Démarré :</strong> {formatDateTime(startedAt)}
            </p>
          )}
          {updatedAt && (
            <p className={fr.cx('fr-mb-0')}>
              <strong>Dernière mise à jour :</strong> {formatDateTime(updatedAt)}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default ProcessingStatus;
