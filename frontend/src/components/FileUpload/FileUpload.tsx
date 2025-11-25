import React, { useCallback, useState, useRef, useEffect } from 'react';
import { Upload } from '@codegouvfr/react-dsfr/Upload';
import { Button } from '@codegouvfr/react-dsfr/Button';
import { Alert } from '@codegouvfr/react-dsfr/Alert';
import { Card } from '@codegouvfr/react-dsfr/Card';
import { Badge } from '@codegouvfr/react-dsfr/Badge';
import { fr } from '@codegouvfr/react-dsfr';
import { useProcessingStore } from '../../stores/processingStore';
import styles from './FileUpload.module.css';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  onStartProcessing: () => void;
  disabled?: boolean;
  isFormValid: boolean;
  autoFocus?: boolean;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB in bytes

export const FileUpload: React.FC<FileUploadProps> = ({
  onFileSelect,
  onStartProcessing,
  disabled = false,
  isFormValid,
  autoFocus = false
}) => {
  const { uploadedFile, error, processingStatus } = useProcessingStore();
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [fileStats, setFileStats] = useState<{ lines: number; size: string } | null>(null);
  const uploadRef = useRef<HTMLDivElement>(null);
  const dropZoneRef = useRef<HTMLButtonElement | null>(null);
  const isProcessing = processingStatus !== 'idle' && processingStatus !== 'failed';

  const validateFile = useCallback((file: File): string | null => {
    // Check file type
    if (file.type !== 'application/json' && !file.name.toLowerCase().endsWith('.json')) {
      return 'Seuls les fichiers JSON sont acceptés.';
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return `Le fichier est trop volumineux. Taille maximale autorisée : ${MAX_FILE_SIZE / (1024 * 1024)}MB.`;
    }

    return null;
  }, []);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const analyzeFile = useCallback(async (file: File) => {
    try {
      const text = await file.text();
      const json = JSON.parse(text);
      const lines = Array.isArray((json as any)?.amendements) ? (json as any).amendements.length : 0;

      setFileStats({
        lines,
        size: formatFileSize(file.size)
      });
    } catch (e) {
      // If parsing fails, just set basic stats
      setFileStats({
        lines: 0,
        size: formatFileSize(file.size)
      });
    }
  }, []);

  const handleFileChange = useCallback(
    (files: File[]) => {
      if (files.length === 0) return;

      const file = files[0];
      const fileValidationError = validateFile(file);

      if (fileValidationError) {
        setValidationError(fileValidationError);
        return;
      }

      setValidationError(null);
      onFileSelect(file);
      analyzeFile(file);
    },
    [onFileSelect, validateFile, analyzeFile]
  );

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setDragActive(true);
    }
  }, []);

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (disabled) return;

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const files = Array.from(e.dataTransfer.files);
        handleFileChange(files);
      }
    },
    [disabled, handleFileChange]
  );

  const handleClick = useCallback(() => {
    if (disabled || isProcessing) return;
    const fileInput = uploadRef.current?.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      fileInput.click();
    }
  }, [disabled, isProcessing]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleClick();
      }
    },
    [handleClick]
  );

  const handleRemoveFile = useCallback(() => {
    onFileSelect(null as any);
    setFileStats(null);
  }, [onFileSelect]);

  // Add event listener to the file input for browser file selection
  useEffect(() => {
    const fileInput = uploadRef.current?.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      const handleInputChange = (e: Event) => {
        const target = e.target as HTMLInputElement;
        if (target.files && target.files.length > 0) {
          const files = Array.from(target.files);
          handleFileChange(files);
        }
      };

      fileInput.addEventListener('change', handleInputChange);
      return () => {
        fileInput.removeEventListener('change', handleInputChange);
      };
    }
  }, [handleFileChange]);

  useEffect(() => {
    if (autoFocus && !disabled && !isProcessing && !uploadedFile && dropZoneRef.current) {
      dropZoneRef.current.focus();
    }
  }, [autoFocus, disabled, isProcessing, uploadedFile]);

  const dropZoneClasses = [
    styles.dropZone,
    dragActive && styles.dragActive,
    (disabled || isProcessing) && styles.disabled
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={fr.cx('fr-mb-4w')}>
      {!uploadedFile ? (
        <button
          ref={dropZoneRef}
          className={dropZoneClasses}
          tabIndex={disabled || isProcessing ? -1 : 0}
          aria-label="Zone de dépôt pour fichier JSON. Cliquez pour sélectionner un fichier ou glissez-déposez un fichier ici."
          aria-describedby="upload-hint"
          onDragEnter={handleDragIn}
          onDragLeave={handleDragOut}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onKeyDown={handleKeyDown}
          onClick={handleClick}
        >
          <div className={styles.dropZoneContent}>
            <div className={styles.iconContainer}>
              <span
                className={`${fr.cx('fr-icon-upload-line')} ${styles.uploadIcon}`}
                aria-hidden="true"
              />
            </div>
            <p className={`${fr.cx('fr-text--lg', 'fr-text--bold')} ${styles.mainText}`}>
              {dragActive
                ? 'Déposez votre fichier JSON ici'
                : 'Glissez-déposez votre fichier JSON ici'}
            </p>
            <p className={`${fr.cx('fr-text--sm')} ${styles.secondaryText}`}>
              ou cliquez pour sélectionner un fichier
            </p>
            <p
              id="upload-hint"
              className={`${fr.cx('fr-text--xs')} ${styles.hintText}`}
            >
              Taille maximale : 50MB. Seuls les fichiers JSON sont acceptés.
            </p>
          </div>

          <div ref={uploadRef} className={styles.hiddenUpload}>
            <Upload
              label="Fichier JSON des amendements"
              hint="Taille maximale : 50MB. Seuls les fichiers JSON sont acceptés."
              state={validationError || error ? 'error' : 'default'}
              stateRelatedMessage={validationError || error || undefined}
              disabled={disabled || isProcessing}
              multiple={false}
            />
          </div>
        </button>
      ) : (
        <>
          <Card
            border={true}
            horizontal
            title={uploadedFile.name}
            start={
              <ul className={fr.cx('fr-badges-group', 'fr-badges-group--sm')}>
                <li>
                  <Badge small>
                    <span className={fr.cx('fr-icon-database-line', 'fr-icon--sm', 'fr-mr-1v')} aria-hidden="true" />
                    {fileStats ? fileStats.size : formatFileSize(uploadedFile.size)}
                  </Badge>
                </li>
                {fileStats && fileStats.lines > 0 && (
                  <li>
                    <Badge small>
                      <span className="fr-icon-file-text-line fr-icon--sm fr-mr-1v" aria-hidden="true" />
                      {fileStats.lines} amendement{fileStats.lines > 1 ? 's' : ''}
                    </Badge>
                  </li>
                )}
              </ul>
            }
            endDetail={
              <>
                <Button
                  className={fr.cx('fr-mr-1w')}
                  priority="secondary"
                  size="small"
                  onClick={handleClick}
                  disabled={disabled || isProcessing}
                  iconId="fr-icon-refresh-line"
                >
                  Changer
                </Button>
                <Button
                  priority="secondary"
                  size="small"
                  onClick={handleRemoveFile}
                  disabled={disabled || isProcessing}
                  iconId="fr-icon-delete-line"
                >
                  Supprimer
                </Button>
              </>
            }
          />

          <div ref={uploadRef} className={styles.hiddenUpload}>
            <Upload
              label="Fichier JSON des amendements"
              hint="Taille maximale : 50MB. Seuls les fichiers JSON sont acceptés."
              state={validationError || error ? 'error' : 'default'}
              stateRelatedMessage={validationError || error || undefined}
              disabled={disabled || isProcessing}
              multiple={false}
            />
          </div>
        </>
      )}

      {validationError && (
        <Alert
          severity="error"
          title="Erreur"
          description={validationError}
          small
          className={fr.cx('fr-mt-2w')}
        />
      )}


    </div>
  );
};

export default FileUpload;
