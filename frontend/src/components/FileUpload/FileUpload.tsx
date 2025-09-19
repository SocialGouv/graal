import React, { useCallback, useState, useRef } from 'react';
import { Upload } from '@codegouvfr/react-dsfr/Upload';
import { Alert } from '@codegouvfr/react-dsfr/Alert';
import { fr } from '@codegouvfr/react-dsfr';
import { useProcessingStore } from '../../stores/processingStore';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB in bytes

export const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect, disabled = false }) => {
  const { uploadedFile, error, processingStatus } = useProcessingStore();
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const uploadRef = useRef<HTMLDivElement>(null);
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

  const handleFileChange = useCallback((files: File[]) => {
    if (files.length === 0) return;

    const file = files[0];
    const validationError = validateFile(file);

    if (validationError) {
      setValidationError(validationError);
      return;
    }

    setValidationError(null);
    onFileSelect(file);
  }, [onFileSelect, validateFile]);

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

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      handleFileChange(files);
    }
  }, [disabled, handleFileChange]);

  const handleClick = useCallback(() => {
    if (disabled || isProcessing) return;
    // Trigger the file input click
    const fileInput = uploadRef.current?.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      fileInput.click();
    }
  }, [disabled, isProcessing]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }, [handleClick]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={fr.cx('fr-mb-4w')}>
      <button
        className={fr.cx('fr-upload-group')}
        tabIndex={disabled || isProcessing ? -1 : 0}
        aria-label="Zone de dépôt pour fichier JSON. Cliquez pour sélectionner un fichier ou glissez-déposez un fichier ici."
        aria-describedby="upload-hint"
        onDragEnter={handleDragIn}
        onDragLeave={handleDragOut}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onKeyDown={handleKeyDown}
        onClick={handleClick}
        style={{
          position: 'relative',
          minHeight: '200px',
          border: dragActive ? '2px solid #000091' : '2px dashed #929292',
          borderRadius: '4px',
          backgroundColor: dragActive ? 'rgba(0, 0, 145, 0.05)' : '#f6f6f6',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: disabled || isProcessing ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s ease-in-out',
          outline: 'none',
        }}
        onFocus={(e) => {
          e.currentTarget.style.boxShadow = '0 0 0 2px #000091';
        }}
        onBlur={(e) => {
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        <div className={fr.cx('fr-mb-2w')} style={{ textAlign: 'center' }}>
          <div className={fr.cx('fr-mb-1w')}>
            <svg
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              style={{ color: dragActive ? '#000091' : '#666666' }}
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14,2 14,8 20,8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10,9 9,9 8,9" />
            </svg>
          </div>
          <p className={fr.cx('fr-text--lg', 'fr-text--bold', 'fr-mb-1v')}>
            {dragActive ? 'Déposez votre fichier JSON ici' : 'Glissez-déposez votre fichier JSON ici'}
          </p>
          <p className={fr.cx('fr-text--sm')} style={{ color: '#666666' }}>
            ou cliquez pour sélectionner un fichier
          </p>
        </div>

        <div ref={uploadRef} style={{ opacity: 0, position: 'absolute', pointerEvents: 'none' }}>
          <Upload
            label="Fichier JSON des amendements"
            hint="Taille maximale : 50MB. Seuls les fichiers JSON sont acceptés."
            state={validationError || error ? 'error' : 'default'}
            stateRelatedMessage={validationError || error || undefined}
            disabled={disabled || isProcessing}
            multiple={false}
          />
        </div>

        <div id="upload-hint" className={fr.cx('fr-text--xs', 'fr-mt-2w')} style={{ color: '#666666' }}>
          Taille maximale : 50MB. Seuls les fichiers JSON sont acceptés.
        </div>
      </button>

      {uploadedFile && (
        <div className={fr.cx('fr-mt-2w')}>
          <Alert
            severity="success"
            title="Fichier sélectionné"
            description={
              <div>
                <strong>{uploadedFile.name}</strong>
                <br />
                Taille : {formatFileSize(uploadedFile.size)}
                <br />
                Type : {uploadedFile.type || 'application/json'}
              </div>
            }
          />
        </div>
      )}

      {(validationError || error) && (
        <div className={fr.cx('fr-mt-2w')}>
          <Alert
            severity="error"
            title="Erreur"
            description={validationError || error || undefined}
          />
        </div>
      )}
    </div>
  );
};

export default FileUpload;
