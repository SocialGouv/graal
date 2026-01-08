import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Badge } from '@codegouvfr/react-dsfr/Badge'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Card } from '@codegouvfr/react-dsfr/Card'
import { Upload } from '@codegouvfr/react-dsfr/Upload'
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useProcessingStore } from '../../stores/processingStore'
import { MultiCombobox } from '../Combobox'
import styles from './FileUpload.module.css'

interface FileUploadProps {
  onFileSelect: (file: File | null) => void
  disabled?: boolean
}

const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB in bytes

type UploadedJson = {
  amendements?: Array<{ mission_titre_court?: unknown }>
}

const extractMissionsFromJson = (json: unknown): string[] => {
  if (!json || typeof json !== 'object') return []

  const amendements = (json as UploadedJson).amendements
  if (!Array.isArray(amendements)) return []

  const missions: string[] = []
  for (const amdt of amendements) {
    const raw = amdt?.mission_titre_court
    if (typeof raw === 'string') {
      const trimmed = raw.trim()
      if (trimmed.length > 0) missions.push(trimmed)
    }
  }

  return Array.from(new Set(missions)).sort((a, b) => a.localeCompare(b))
}

const readFileAsText = async (file: File): Promise<string> => {
  // We prefer FileReader for maximum compatibility across browsers and jsdom.
  const text = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()

    reader.onerror = () => {
      reject(reader.error ?? new Error('Failed to read file'))
    }

    reader.onload = () => {
      resolve(String(reader.result ?? ''))
    }

    reader.readAsText(file)
  })

  // Defensive: strip UTF-8 BOM if present
  return text.replace(/^\uFEFF/, '')
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFileSelect,
  disabled = false
}) => {
  const {
    uploadedFile,
    error,
    processingStatus,
    processingConfig,
    setProcessingConfig
  } = useProcessingStore()
  const [dragActive, setDragActive] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [fileStats, setFileStats] = useState<{
    lines: number
    size: string
  } | null>(null)
  const [availableMissions, setAvailableMissions] = useState<string[]>([])
  const uploadRef = useRef<HTMLDivElement>(null)
  const isProcessing =
    processingStatus !== 'idle' && processingStatus !== 'failed'

  const selectedMissions = processingConfig.missionShortTitleFilter

  const validateFile = useCallback((file: File): string | null => {
    // Check file type
    if (
      file.type !== 'application/json' &&
      !file.name.toLowerCase().endsWith('.json')
    ) {
      return 'Seuls les fichiers JSON sont acceptés.'
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return `Le fichier est trop volumineux. Taille maximale autorisée : ${MAX_FILE_SIZE / (1024 * 1024)}MB.`
    }

    return null
  }, [])

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const analyzeFile = useCallback(
    async (file: File) => {
      try {
        const text = await readFileAsText(file)
        const json: unknown = JSON.parse(text)

        const missions = extractMissionsFromJson(json)
        setAvailableMissions(missions)

        // If missions changed, drop previously selected missions that are no longer present
        if (missions.length > 0 && selectedMissions.length > 0) {
          const retained = selectedMissions.filter((m) => missions.includes(m))
          if (retained.length !== selectedMissions.length) {
            setProcessingConfig({
              ...processingConfig,
              missionShortTitleFilter: retained
            })
          }
        }

        const lines = Array.isArray((json as any)?.amendements)
          ? (json as any).amendements.length
          : 0

        setFileStats({
          lines,
          size: formatFileSize(file.size)
        })
      } catch {
        // If parsing fails, just set basic stats
        setFileStats({
          lines: 0,
          size: formatFileSize(file.size)
        })
        setAvailableMissions([])
      }
    },
    [formatFileSize, processingConfig, selectedMissions, setProcessingConfig]
  )

  const handleFileChange = useCallback(
    (files: File[]) => {
      if (files.length === 0) return

      const file = files[0]
      const fileValidationError = validateFile(file)

      if (fileValidationError) {
        setValidationError(fileValidationError)
        return
      }

      setValidationError(null)
      onFileSelect(file)
      analyzeFile(file)
    },
    [onFileSelect, validateFile, analyzeFile]
  )

  // If the user navigates away and comes back while a file is already selected,
  // we need to restore the derived mission list from the stored File object.
  useEffect(() => {
    if (!uploadedFile) return
    if (availableMissions.length > 0) return

    void analyzeFile(uploadedFile)
  }, [analyzeFile, availableMissions.length, uploadedFile])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setDragActive(true)
    }
  }, [])

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragActive(false)

      if (disabled) return

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const files = Array.from(e.dataTransfer.files)
        handleFileChange(files)
      }
    },
    [disabled, handleFileChange]
  )

  const handleClick = useCallback(() => {
    if (disabled || isProcessing) return
    const fileInput = uploadRef.current?.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement
    if (fileInput) {
      fileInput.click()
    }
  }, [disabled, isProcessing])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        handleClick()
      }
    },
    [handleClick]
  )

  const handleRemoveFile = useCallback(() => {
    onFileSelect(null)
    setFileStats(null)
    setAvailableMissions([])
    setProcessingConfig({
      ...processingConfig,
      missionShortTitleFilter: []
    })
  }, [onFileSelect, processingConfig, setProcessingConfig])

  const handleClearMissions = useCallback(() => {
    setProcessingConfig({
      ...processingConfig,
      missionShortTitleFilter: []
    })
  }, [processingConfig, setProcessingConfig])

  // Add event listener to the file input for browser file selection
  useEffect(() => {
    const fileInput = uploadRef.current?.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement
    if (fileInput) {
      const handleInputChange = (e: Event) => {
        const target = e.target as HTMLInputElement
        if (target.files && target.files.length > 0) {
          const files = Array.from(target.files)
          handleFileChange(files)
        }
      }

      fileInput.addEventListener('change', handleInputChange)
      return () => {
        fileInput.removeEventListener('change', handleInputChange)
      }
    }
  }, [handleFileChange])

  const dropZoneClasses = [
    styles.dropZone,
    dragActive && styles.dragActive,
    (disabled || isProcessing) && styles.disabled
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={fr.cx('fr-mb-4w')}>
      {!uploadedFile ? (
        <button
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
            <p
              className={`${fr.cx('fr-text--lg', 'fr-text--bold')} ${styles.mainText}`}
            >
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
                    <span
                      className={fr.cx(
                        'fr-icon-database-line',
                        'fr-icon--sm',
                        'fr-mr-1v'
                      )}
                      aria-hidden="true"
                    />
                    {fileStats
                      ? fileStats.size
                      : formatFileSize(uploadedFile.size)}
                  </Badge>
                </li>
                {fileStats && fileStats.lines > 0 && (
                  <li>
                    <Badge small>
                      <span
                        className="fr-icon-file-text-line fr-icon--sm fr-mr-1v"
                        aria-hidden="true"
                      />
                      {fileStats.lines} amendement
                      {fileStats.lines > 1 ? 's' : ''}
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

          <div className={fr.cx('fr-mt-4w')}>
            <h3 className={fr.cx('fr-h6', 'fr-mb-1w')}>Filtrer par mission</h3>

            {availableMissions.length === 0 ? (
              <p className={fr.cx('fr-text--sm', 'fr-hint-text')}>
                Aucune mission détectée dans ce fichier.
              </p>
            ) : (
              <>
                <MultiCombobox
                  options={availableMissions}
                  values={selectedMissions}
                  onChange={(values) => {
                    setProcessingConfig({
                      ...processingConfig,
                      missionShortTitleFilter: values
                    })
                  }}
                  label="Missions sélectionnées"
                  hint="Cliquez sur une mission pour l’ajouter au filtre. Supprimez une mission avec la croix ou la touche retour arrière."
                  disabled={disabled || isProcessing}
                  emptyMessage="Aucune mission trouvée"
                  state={validationError || error ? 'error' : 'default'}
                  stateRelatedMessage={validationError || error || undefined}
                />

                {selectedMissions.length > 0 && (
                  <div className={fr.cx('fr-mt-2w')}>
                    <Button
                      type="button"
                      priority="secondary"
                      size="small"
                      onClick={handleClearMissions}
                      disabled={disabled || isProcessing}
                    >
                      Tout effacer
                    </Button>
                  </div>
                )}
              </>
            )}
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
  )
}

export default FileUpload
