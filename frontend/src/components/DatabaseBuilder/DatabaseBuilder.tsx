import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Badge } from '@codegouvfr/react-dsfr/Badge'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { ButtonsGroup } from '@codegouvfr/react-dsfr/ButtonsGroup'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Select } from '@codegouvfr/react-dsfr/Select'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { Tabs } from '@codegouvfr/react-dsfr/Tabs'
import { useMutation, useQuery } from '@tanstack/react-query'
import React, { useEffect, useRef, useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { apiService } from '../../services/api'
import {
  selectActiveJobs,
  useJobsStore,
  type TrackedJob
} from '../../stores/jobsStore'
import { useProcessingStore } from '../../stores/processingStore'
import type { FileReference, FileReferenceWithMetadata } from '../../types/api'
import { ConfigFileSelector } from '../ConfigFileSelector'
import { ManageDatabases } from '../ManageDatabases/ManageDatabases'

interface PendingFile {
  file: File
  timestamp: string
  originProject: string
  id: string
  dateAutoExtracted?: boolean
}

type BuildMode = 'create' | 'append'

/**
 * Extract date from amendment JSON file content.
 * Looks for first non-empty date_derniere_modif in amendments array.
 * @param fileContent - JSON file content as string
 * @returns Formatted date string (YYYY-MM-DD) or null if not found
 */
const extractDateFromAmendmentJSON = (fileContent: string): string | null => {
  try {
    const json = JSON.parse(fileContent)

    // Look for amendments array
    if (!json.amendements || !Array.isArray(json.amendements)) {
      return null
    }

    // Find first amendment with non-empty date_derniere_modif
    for (const amendment of json.amendements) {
      if (amendment.date_derniere_modif) {
        // Convert datetime string to YYYY-MM-DD format
        const dateStr = amendment.date_derniere_modif
        const date = new Date(dateStr)

        if (!Number.isNaN(date.getTime())) {
          // Format as YYYY-MM-DD
          const year = date.getFullYear()
          const month = String(date.getMonth() + 1).padStart(2, '0')
          const day = String(date.getDate()).padStart(2, '0')
          return `${year}-${month}-${day}`
        }
      }
    }

    return null
  } catch (error) {
    console.error('Error extracting date from JSON:', error)
    return null
  }
}

export const DatabaseBuilder: React.FC = () => {
  const { user, isAdmin, isLoading: authLoading } = useAuth()
  const {
    databaseBuilder,
    setDatabaseConfigFile,
    setDatabaseName,
    addUploadedFile,
    removeUploadedFile,
    clearUploadedFiles,
    setJobId
  } = useProcessingStore()

  const { registerJob, addToast, jobs } = useJobsStore()

  const [mode, setMode] = useState<BuildMode>('create')
  const [selectedDatabase, setSelectedDatabase] = useState<string>('')
  const [selectedDatabaseId, setSelectedDatabaseId] = useState<string>('')
  const [existingFiles, setExistingFiles] = useState<
    FileReferenceWithMetadata[]
  >([])
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [buildError, setBuildError] = useState<string | null>(null)
  const [manifestError, setManifestError] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState<boolean>(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const ProgressBar = ({ percent }: { percent: number }) => (
    <div
      style={{
        width: '100%',
        height: '8px',
        backgroundColor: '#e5e5e5',
        borderRadius: '4px',
        overflow: 'hidden'
      }}
      aria-label={`Progression ${percent}%`}
    >
      <div
        style={{
          width: `${Math.max(0, Math.min(100, percent))}%`,
          height: '100%',
          backgroundColor: '#000091',
          transition: 'width 0.3s ease'
        }}
      />
    </div>
  )

  // Query for listing databases
  const { data: databaseList } = useQuery({
    queryKey: ['databases'],
    queryFn: () => apiService.listDatabases(),
    refetchInterval: false
  })

  // Query for listing databases the user can append to
  const { data: appendableDatabaseList } = useQuery({
    queryKey: ['appendable-databases'],
    queryFn: () => apiService.listAppendableDatabases(),
    enabled: mode === 'append',
    refetchInterval: false
  })

  const activeDbJobForCurrentSelection: TrackedJob | undefined = (() => {
    const active = selectActiveJobs(jobs)
    const dbJobs = active.filter(
      (j) => j.kind === 'database_build' || j.kind === 'database_append'
    )

    // Append mode: strictly by databaseId (as requested)
    if (mode === 'append' && selectedDatabaseId) {
      return dbJobs.find((j) => j.context?.databaseId === selectedDatabaseId)
    }

    // Create mode: no ID exists yet. We still display a best-effort progress indicator,
    // but we DO NOT use it to block the button.
    if (mode === 'create' && databaseBuilder.databaseName) {
      return dbJobs.find(
        (j) =>
          j.kind === 'database_build' &&
          j.context?.databaseName === databaseBuilder.databaseName
      )
    }

    return undefined
  })()

  const isDbBuildOngoingBlocking =
    mode === 'append' && Boolean(activeDbJobForCurrentSelection)

  // Query for loading manifest in append mode
  const {
    data: manifest,
    isLoading: isLoadingManifest,
    error: manifestQueryError
  } = useQuery({
    queryKey: ['database-manifest', selectedDatabase],
    queryFn: () => apiService.getDatabaseManifest(selectedDatabase),
    enabled: mode === 'append' && selectedDatabase !== '',
    retry: false
  })

  // Update existing files when manifest is loaded
  useEffect(() => {
    if (manifest) {
      setExistingFiles(manifest.files)
      setManifestError(null)
    }
  }, [manifest])

  // Handle manifest loading errors
  useEffect(() => {
    if (manifestQueryError) {
      const error = manifestQueryError as any
      setManifestError(
        error.detail || error.message || 'Failed to load database manifest'
      )
      setExistingFiles([])
    }
  }, [manifestQueryError])

  // Reset state when mode changes
  useEffect(() => {
    if (mode === 'create') {
      setSelectedDatabase('')
      setSelectedDatabaseId('')
      setExistingFiles([])
      setManifestError(null)
    } else {
      // Reset database name in append mode
      setDatabaseName('')
      setSelectedDatabase('')
      setSelectedDatabaseId('')
      // Clear any uploaded files when switching to append
      setPendingFiles([])
    }
    // Clear errors when switching modes
    setBuildError(null)
  }, [mode, setDatabaseName])

  // Mutation for file upload
  const uploadMutation = useMutation({
    mutationFn: (params: {
      file: File
      metadata: {
        default_processing_timestamp?: number
        origin_project: string
      }
      dateAutoExtracted: boolean
    }) => apiService.uploadAmendmentFile(params.file, params.metadata),
    onSuccess: (data, variables) => {
      // Use the timestamp from the metadata we sent to backend
      const timestamp = variables.metadata.default_processing_timestamp!

      addUploadedFile({
        uploadId: data.upload_id,
        filename: data.filename,
        fileHash: data.file_hash,
        s3Key: data.s3_key,
        size: data.size,
        timestamp,
        originProject: variables.metadata.origin_project,
        dateAutoExtracted: variables.dateAutoExtracted
      })

      setUploadError(null)
    },
    onError: (error: Error) => {
      setUploadError(error.message || 'Failed to upload file')
    }
  })

  // Mutation for building database
  const buildMutation = useMutation({
    mutationFn: (fileReferences: FileReference[]) => {
      return apiService.buildDatabase({
        config_file_id: databaseBuilder.selectedConfigFile!,
        database_name: databaseBuilder.databaseName,
        file_references: fileReferences
      })
    },
    onSuccess: (data) => {
      setJobId(data.job_id)
      registerJob({
        jobId: data.job_id,
        kind: 'database_build',
        label: `Construction base ${databaseBuilder.databaseName}`,
        context: { databaseName: databaseBuilder.databaseName }
      })
      addToast({
        severity: 'info',
        title: `Construction base ${databaseBuilder.databaseName} — démarrée`,
        description: `Job ${data.job_id}`
      })
      setBuildError(null)
      // Clear uploaded files after successful build
      clearUploadedFiles()
    },
    onError: (error: any) => {
      setBuildError(error.detail || error.message || 'Failed to build database')
    }
  })

  // Mutation for appending to database
  const appendMutation = useMutation({
    mutationFn: () => {
      // Check for duplicate hashes between new and existing files
      const existingHashes = new Set(existingFiles.map((f) => f.file_hash))

      const duplicates = databaseBuilder.uploadedFiles.filter((f) =>
        existingHashes.has(f.fileHash)
      )

      if (duplicates.length > 0) {
        throw new Error(
          `${duplicates.length} fichier(s) existe(nt) déjà dans la base de données : ${duplicates.map((d) => d.filename).join(', ')}`
        )
      }

      // Combine existing files with newly uploaded files
      const newFileReferences = databaseBuilder.uploadedFiles.map((file) => ({
        upload_id: file.uploadId,
        filename: file.filename,
        file_hash: file.fileHash,
        s3_key: file.s3Key,
        metadata: {
          default_processing_timestamp: file.timestamp,
          origin_project: file.originProject
        }
      }))

      return apiService.appendToDatabase(selectedDatabase, {
        config_file_id: databaseBuilder.selectedConfigFile!,
        file_references: newFileReferences
      })
    },
    onSuccess: (data) => {
      setJobId(data.job_id)
      registerJob({
        jobId: data.job_id,
        kind: 'database_append',
        label: `Reconstruction base ${selectedDatabase}`,
        context: {
          databaseName: selectedDatabase,
          databaseId: selectedDatabaseId
        }
      })
      addToast({
        severity: 'info',
        title: `Reconstruction base ${selectedDatabase} — démarrée`,
        description: `Job ${data.job_id}`
      })
      setBuildError(null)
      // Clear uploaded files after successful append
      clearUploadedFiles()
    },
    onError: (error: any) => {
      setBuildError(
        error.detail || error.message || 'Failed to append to database'
      )
    }
  })

  // Mutation for deleting uploaded file
  const deleteMutation = useMutation({
    mutationFn: (uploadId: string) => apiService.deleteUploadedFile(uploadId),
    onSuccess: (_data, uploadId) => {
      removeUploadedFile(uploadId)
    }
  })

  // Process files helper function to extract dates and create pending files
  const processFiles = async (files: FileList | File[]) => {
    setUploadError(null)

    const filePromises = Array.from(files).map(async (file) => {
      const pendingFile: PendingFile = {
        file,
        timestamp: '',
        originProject: '',
        id: crypto.randomUUID(),
        dateAutoExtracted: false
      }

      // Try to extract date from JSON files
      if (file.name.toLowerCase().endsWith('.json')) {
        try {
          const fileContent = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader()
            reader.onload = (event) => resolve(event.target?.result as string)
            reader.onerror = (error) => reject(error)
            reader.readAsText(file)
          })

          const extractedDate = extractDateFromAmendmentJSON(fileContent)
          if (extractedDate) {
            pendingFile.timestamp = extractedDate
            pendingFile.dateAutoExtracted = true
          }
        } catch (error) {
          console.error(`Failed to read file ${file.name}:`, error)
        }
      }

      return pendingFile
    })

    const newPendingFiles = await Promise.all(filePromises)
    setPendingFiles((prev) => [...prev, ...newPendingFiles])
  }

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      await processFiles(files)
    }
  }

  const handleFileInputChange = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const files = e.target.files
    if (files && files.length > 0) {
      await processFiles(files)
      // Reset the input to allow re-selecting the same files
      e.target.value = ''
    }
  }

  const handleBatchUpload = async () => {
    // Validate all pending files have both origin_project AND timestamp
    const filesWithoutProject = pendingFiles.filter((pf) => !pf.originProject)
    const filesWithoutTimestamp = pendingFiles.filter((pf) => !pf.timestamp)

    if (filesWithoutProject.length > 0) {
      setUploadError(
        `${filesWithoutProject.length} fichier(s) n'ont pas de projet d'origine. Veuillez remplir le projet d'origine pour tous les fichiers.`
      )
      return
    }

    if (filesWithoutTimestamp.length > 0) {
      setUploadError(
        `${filesWithoutTimestamp.length} fichier(s) n'ont pas d'horodatage. Veuillez fournir un horodatage pour tous les fichiers avant le téléchargement.`
      )
      return
    }

    if (pendingFiles.length === 0) {
      setUploadError('Aucun fichier à télécharger')
      return
    }

    setUploadError(null)

    // Upload files sequentially
    for (const pendingFile of pendingFiles) {
      try {
        // Build metadata - only include timestamp if provided by user
        const metadata: {
          default_processing_timestamp?: number
          origin_project: string
        } = {
          origin_project: pendingFile.originProject
        }

        if (pendingFile.timestamp) {
          // Parse date as YYYY-MM-DD, create Date at 00:00 UTC
          const [year, month, day] = pendingFile.timestamp
            .split('-')
            .map(Number)
          metadata.default_processing_timestamp =
            Date.UTC(year, month - 1, day) / 1000
        }

        await uploadMutation.mutateAsync({
          file: pendingFile.file,
          metadata,
          dateAutoExtracted: pendingFile.dateAutoExtracted || false
        })
      } catch (error) {
        setUploadError(
          `Erreur lors du téléchargement de ${pendingFile.file.name}: ${error instanceof Error ? error.message : 'Erreur inconnue'}`
        )
        return // Stop on first error
      }
    }

    // Clear pending files after successful upload of all files
    setPendingFiles([])
  }

  const handleBuildDatabase = () => {
    // Validate common requirements
    const validateCommonRequirements = (): string | null => {
      if (!databaseBuilder.selectedConfigFile) {
        return 'Veuillez sélectionner un fichier de configuration'
      }

      if (databaseBuilder.uploadedFiles.length === 0) {
        return 'Veuillez télécharger au moins un fichier'
      }

      const filesWithoutTimestamp = databaseBuilder.uploadedFiles.filter(
        (file) => !file.timestamp
      )

      if (filesWithoutTimestamp.length > 0) {
        const action =
          mode === 'create'
            ? 'avant de construire la base de données'
            : 'avant de reconstruire la base de données'
        return `${filesWithoutTimestamp.length} fichier(s) n'ont pas d'horodatage. Veuillez fournir un horodatage pour tous les fichiers ${action}.`
      }

      return null
    }

    // Validate create mode specific requirements
    const validateCreateMode = (): string | null => {
      if (!databaseBuilder.databaseName) {
        return 'Veuillez fournir un nom de base de données'
      }
      return null
    }

    // Validate append mode specific requirements
    const validateAppendMode = (): string | null => {
      if (!selectedDatabase) {
        return 'Veuillez sélectionner une base de données existante'
      }
      return null
    }

    // Build file references (shared logic)
    const buildFileReferences = (): FileReference[] => {
      return databaseBuilder.uploadedFiles.map((file) => ({
        upload_id: file.uploadId,
        filename: file.filename,
        file_hash: file.fileHash,
        s3_key: file.s3Key,
        metadata: {
          default_processing_timestamp: file.timestamp,
          origin_project: file.originProject
        }
      }))
    }

    // Validate common requirements
    const commonError = validateCommonRequirements()
    if (commonError) {
      setBuildError(commonError)
      return
    }

    // Mode-specific validation and execution
    if (mode === 'create') {
      const createError = validateCreateMode()
      if (createError) {
        setBuildError(createError)
        return
      }

      const fileReferences = buildFileReferences()
      buildMutation.mutate(fileReferences)
    } else {
      const appendError = validateAppendMode()
      if (appendError) {
        setBuildError(appendError)
        return
      }

      appendMutation.mutate()
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  // Check if user can manage databases (owns at least one or is admin)
  const { data: managedDatabases } = useQuery({
    queryKey: ['managed-databases'],
    queryFn: () => apiService.getManagedDatabases(),
    enabled: !authLoading && !!user
  })

  const canManageDatabases =
    isAdmin || (managedDatabases && managedDatabases.length > 0)

  const buildDatabaseContent = (
    <>
      <style>{`
        .upload-dropzone {
          border: 2px dashed var(--border-default-grey);
          border-radius: 0.5rem;
          padding: 2rem;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s ease;
          background-color: var(--background-default-grey);
        }

        .upload-dropzone:hover {
          border-color: var(--border-action-high-blue-france);
          background-color: var(--background-contrast-blue-france);
        }

        .upload-dropzone--active {
          border-color: var(--border-action-high-blue-france);
          background-color: var(--background-contrast-blue-france);
          border-style: solid;
        }

        .upload-dropzone__content {
          pointer-events: none;
        }

        .upload-dropzone__text {
          margin: 1rem 0 0.5rem;
          font-weight: 500;
        }

        .upload-dropzone__hint {
          margin: 0;
          font-size: 0.875rem;
          color: var(--text-mention-grey);
        }

        .db-spin {
          display: inline-block;
          animation: db-spin 1s linear infinite;
        }

        @keyframes db-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
      <div>
        <p className={fr.cx('fr-text--lead', 'fr-mb-4w')}>
          Créez des bases de données de similarité à partir de fichiers
          d'amendements pour la recherche de similarité.
        </p>

        {/* Mode Selection */}
        <section className={fr.cx('fr-mb-6w', 'fr-mt-4w')}>
          <h2 className={fr.cx('fr-h4', 'fr-mb-2w')}>Mode de construction</h2>
          <ButtonsGroup
            buttons={[
              {
                children: 'Créer une nouvelle base de données',
                priority: mode === 'create' ? 'primary' : 'secondary',
                onClick: () => {
                  setMode('create')
                  setBuildError(null)
                  setManifestError(null)
                }
              },
              {
                children: 'Ajouter à une base existante',
                priority: mode === 'append' ? 'primary' : 'secondary',
                onClick: () => {
                  setMode('append')
                  setBuildError(null)
                  setManifestError(null)
                }
              }
            ]}
            inlineLayoutWhen="always"
          />
        </section>

        {/* Step 1: Select Config File */}
        <section className={fr.cx('fr-mb-6w', 'fr-mt-4w')}>
          <h2 className={fr.cx('fr-h3')}>
            1. Sélectionner un fichier de configuration
          </h2>
          <p className={fr.cx('fr-text--sm', 'fr-mb-2w')}>
            Choisissez le fichier de configuration contenant les correspondances
            d'acronymes
          </p>
          <ConfigFileSelector
            disabled={false}
            onChange={setDatabaseConfigFile}
            value={databaseBuilder.selectedConfigFile}
          />
        </section>

        {/* Step 2: Database Name or Selection */}
        <section className={fr.cx('fr-mb-6w', 'fr-mt-4w')}>
          {mode === 'create' ? (
            <>
              <h2 className={fr.cx('fr-h3')}>
                2. Nommer votre base de données
              </h2>
              <Input
                label="Nom de la base de données"
                hintText="Choisissez un nom descriptif pour votre base de données (ex: PLFSS_2024)"
                nativeInputProps={{
                  value: databaseBuilder.databaseName,
                  onChange: (e) => setDatabaseName(e.target.value),
                  placeholder: 'ex: PLFSS_2024',
                  disabled: !databaseBuilder.selectedConfigFile
                }}
              />
              {!databaseBuilder.selectedConfigFile && (
                <p className={fr.cx('fr-text--sm', 'fr-hint-text', 'fr-mt-1w')}>
                  Vous devez sélectionner un fichier de configuration pour
                  continuer
                </p>
              )}
            </>
          ) : (
            <>
              <h2 className={fr.cx('fr-h3')}>
                2. Sélectionner une base de données existante
              </h2>
              <Select
                label="Base de données existante"
                hint="Sélectionnez la base de données à laquelle ajouter des fichiers"
                nativeSelectProps={{
                  value: selectedDatabase,
                  onChange: (e) => {
                    const nextName = e.target.value
                    setSelectedDatabase(nextName)
                    const nextDb = appendableDatabaseList?.databases.find(
                      (db) => db.name === nextName
                    )
                    setSelectedDatabaseId(nextDb?.id ?? '')
                    setBuildError(null)
                    setManifestError(null)
                  },
                  disabled: !databaseBuilder.selectedConfigFile
                }}
              >
                <option value="">Sélectionner une base de données</option>
                {appendableDatabaseList?.databases.map((db) => (
                  <option key={db.id} value={db.name}>
                    {db.name}
                  </option>
                ))}
              </Select>
              {!databaseBuilder.selectedConfigFile && (
                <p className={fr.cx('fr-text--sm', 'fr-hint-text', 'fr-mt-1w')}>
                  Vous devez sélectionner un fichier de configuration pour
                  continuer
                </p>
              )}

              {/* Display existing files in database */}
              {existingFiles.length > 0 && (
                <div className={fr.cx('fr-mt-4w')}>
                  <h3 className={fr.cx('fr-h6', 'fr-mb-2w')}>
                    Fichiers existants dans la base de données (
                    {existingFiles.length})
                  </h3>
                  <Table
                    headers={[
                      'Nom de fichier',
                      "Projet d'origine",
                      'Horodatage'
                    ]}
                    data={existingFiles.map((file) => [
                      file.filename,
                      file.metadata.origin_project,
                      new Date(
                        file.metadata.default_processing_timestamp * 1000
                      ).toLocaleDateString('fr-FR')
                    ])}
                  />
                  <Alert
                    severity="info"
                    title="Information"
                    description="La base de données sera reconstruite avec tous les fichiers existants plus les nouveaux fichiers que vous ajouterez."
                    small
                    className={fr.cx('fr-mt-2w')}
                  />
                </div>
              )}

              {isLoadingManifest && (
                <p className={fr.cx('fr-text--sm', 'fr-mt-2w')}>
                  Chargement des fichiers existants...
                </p>
              )}

              {manifestError && (
                <Alert
                  severity="error"
                  title="Erreur"
                  description="Impossible de charger les fichiers existants de cette base de données."
                  className={fr.cx('fr-mt-2w')}
                />
              )}
            </>
          )}
        </section>

        {/* Step 3: Upload Files */}
        <section className={fr.cx('fr-mb-6w')}>
          <h2 className={fr.cx('fr-h3')}>
            3. Télécharger les fichiers d'amendements
          </h2>

          <div className={fr.cx('fr-mb-3w')}>
            <button
              type="button"
              className={`upload-dropzone ${isDragOver ? 'upload-dropzone--active' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  e.stopPropagation()
                  fileInputRef.current?.click()
                }
              }}
              style={{
                opacity:
                  mode === 'create'
                    ? !databaseBuilder.selectedConfigFile ||
                      !databaseBuilder.databaseName
                      ? 0.5
                      : 1
                    : !databaseBuilder.selectedConfigFile || !selectedDatabase
                      ? 0.5
                      : 1,
                pointerEvents:
                  mode === 'create'
                    ? !databaseBuilder.selectedConfigFile ||
                      !databaseBuilder.databaseName
                      ? 'none'
                      : 'auto'
                    : !databaseBuilder.selectedConfigFile || !selectedDatabase
                      ? 'none'
                      : 'auto'
              }}
            >
              <div className="upload-dropzone__content">
                <i
                  className="ri-upload-cloud-line ri-2x"
                  aria-hidden="true"
                ></i>
                <p className="upload-dropzone__text">
                  {isDragOver
                    ? 'Déposez vos fichiers ici'
                    : 'Glissez-déposez vos fichiers ici ou cliquez pour parcourir'}
                </p>
                <p className="upload-dropzone__hint">
                  Formats acceptés : JSON, Excel (.json, .xlsx, .xls)
                </p>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileInputChange}
                accept=".json,.xlsx,.xls"
                multiple
                style={{ display: 'none' }}
                disabled={
                  mode === 'create'
                    ? !databaseBuilder.selectedConfigFile ||
                      !databaseBuilder.databaseName
                    : !databaseBuilder.selectedConfigFile || !selectedDatabase
                }
              />
            </button>
          </div>

          {/* Pending Files Configuration Table */}
          {pendingFiles.length > 0 && (
            <div className={fr.cx('fr-mb-3w')}>
              <h3 className={fr.cx('fr-h6', 'fr-mb-2w')}>
                Fichiers en attente de configuration ({pendingFiles.length})
              </h3>
              <Table
                headers={[
                  'Nom de fichier',
                  'Taille',
                  'Horodatage',
                  "Projet d'origine",
                  'Actions'
                ]}
                data={pendingFiles.map((pendingFile) => [
                  pendingFile.file.name,
                  formatFileSize(pendingFile.file.size),
                  <div
                    key={`timestamp-${pendingFile.id}`}
                    className={fr.cx('fr-raw-list')}
                  >
                    <input
                      type="date"
                      className={fr.cx('fr-input')}
                      value={pendingFile.timestamp}
                      onChange={(e) => {
                        setPendingFiles((prev) =>
                          prev.map((pf) =>
                            pf.id === pendingFile.id
                              ? {
                                  ...pf,
                                  timestamp: e.target.value,
                                  dateAutoExtracted: false
                                }
                              : pf
                          )
                        )
                        setUploadError(null)
                      }}
                    />
                    {pendingFile.dateAutoExtracted && (
                      <Badge
                        severity="success"
                        noIcon
                        small
                        className={fr.cx('fr-mt-1v')}
                      >
                        Auto-extrait
                      </Badge>
                    )}
                  </div>,
                  <input
                    key={`project-${pendingFile.id}`}
                    type="text"
                    className={fr.cx('fr-input')}
                    value={pendingFile.originProject}
                    onChange={(e) => {
                      setPendingFiles((prev) =>
                        prev.map((pf) =>
                          pf.id === pendingFile.id
                            ? { ...pf, originProject: e.target.value }
                            : pf
                        )
                      )
                      setUploadError(null)
                    }}
                    placeholder="ex: PLFSS 2024"
                    required
                  />,
                  <Button
                    key={`remove-${pendingFile.id}`}
                    size="small"
                    priority="tertiary no outline"
                    onClick={() => {
                      setPendingFiles((prev) =>
                        prev.filter((pf) => pf.id !== pendingFile.id)
                      )
                    }}
                    iconId="fr-icon-delete-line"
                  >
                    Retirer
                  </Button>
                ])}
              />
            </div>
          )}

          {uploadError && (
            <Alert
              severity="error"
              title="Erreur de téléchargement"
              description={uploadError}
              className={fr.cx('fr-mb-3w')}
            />
          )}

          <Button
            onClick={handleBatchUpload}
            disabled={
              mode === 'create'
                ? !databaseBuilder.selectedConfigFile ||
                  !databaseBuilder.databaseName ||
                  pendingFiles.length === 0 ||
                  uploadMutation.isPending
                : !databaseBuilder.selectedConfigFile ||
                  !selectedDatabase ||
                  pendingFiles.length === 0 ||
                  uploadMutation.isPending
            }
            iconId="fr-icon-upload-line"
            iconPosition="left"
          >
            {uploadMutation.isPending
              ? 'Téléchargement...'
              : `Télécharger ${pendingFiles.length} fichier(s)`}
          </Button>
          {mode === 'create'
            ? (!databaseBuilder.selectedConfigFile ||
                !databaseBuilder.databaseName) && (
                <p className={fr.cx('fr-text--sm', 'fr-hint-text', 'fr-mt-2w')}>
                  Veuillez compléter les étapes 1 et 2 avant de télécharger des
                  fichiers
                </p>
              )
            : (!databaseBuilder.selectedConfigFile || !selectedDatabase) && (
                <p className={fr.cx('fr-text--sm', 'fr-hint-text', 'fr-mt-2w')}>
                  Veuillez compléter les étapes 1 et 2 avant de télécharger des
                  fichiers
                </p>
              )}

          {/* Uploaded Files Table */}
          {databaseBuilder.uploadedFiles.length > 0 && (
            <div className={fr.cx('fr-mt-4w')}>
              <h3 className={fr.cx('fr-h5')}>
                Fichiers téléchargés ({databaseBuilder.uploadedFiles.length})
              </h3>
              <Table
                headers={[
                  'Nom de fichier',
                  "Projet d'origine",
                  'Horodatage',
                  'Taille',
                  'Actions'
                ]}
                data={databaseBuilder.uploadedFiles.map((file) => [
                  file.filename,
                  file.originProject,
                  <div
                    key={`timestamp-${file.uploadId}`}
                    className={fr.cx('fr-raw-list')}
                  >
                    {new Date(file.timestamp * 1000).toLocaleDateString(
                      'fr-FR'
                    )}
                    {file.dateAutoExtracted && (
                      <Badge
                        severity="success"
                        noIcon
                        small
                        className={fr.cx('fr-ml-1w')}
                      >
                        Auto-extrait
                      </Badge>
                    )}
                  </div>,
                  formatFileSize(file.size),
                  <Button
                    key={file.uploadId}
                    size="small"
                    priority="tertiary no outline"
                    onClick={() => deleteMutation.mutate(file.uploadId)}
                    disabled={deleteMutation.isPending}
                    iconId="fr-icon-delete-line"
                  >
                    Supprimer
                  </Button>
                ])}
              />
            </div>
          )}
        </section>

        {/* Step 4: Build Database */}
        <section className={fr.cx('fr-mb-6w')}>
          <h2 className={fr.cx('fr-h3')}>
            4.{' '}
            {mode === 'create'
              ? 'Construire la base de données'
              : 'Reconstruire la base de données'}
          </h2>
          <p>
            {mode === 'create'
              ? 'Cela traitera tous les fichiers téléchargés et créera une base de données de similarité qui pourra être utilisée pour les opérations de recherche de similarité.'
              : 'Cela reconstruira la base de données avec tous les fichiers existants plus les nouveaux fichiers ajoutés.'}
          </p>

          {buildError && (
            <Alert
              severity="error"
              title="Erreur de construction"
              description={buildError}
              className={fr.cx('fr-mb-3w')}
            />
          )}

          <Button
            onClick={handleBuildDatabase}
            disabled={
              mode === 'create'
                ? !databaseBuilder.selectedConfigFile ||
                  !databaseBuilder.databaseName ||
                  databaseBuilder.uploadedFiles.length === 0 ||
                  buildMutation.isPending
                : !databaseBuilder.selectedConfigFile ||
                  !selectedDatabase ||
                  databaseBuilder.uploadedFiles.length === 0 ||
                  appendMutation.isPending ||
                  isDbBuildOngoingBlocking
            }
            iconId="fr-icon-checkbox-circle-line"
            iconPosition="left"
            className="fr-btn--block"
          >
            <span className={fr.cx('fr-mr-1w')}>
              {activeDbJobForCurrentSelection && (
                <i className="ri-loader-4-line db-spin" />
              )}
            </span>
            {mode === 'create'
              ? activeDbJobForCurrentSelection || buildMutation.isPending
                ? 'Construction en cours...'
                : 'Construire la base de données'
              : activeDbJobForCurrentSelection || appendMutation.isPending
                ? 'Reconstruction en cours...'
                : 'Reconstruire la base de données'}
          </Button>

          {activeDbJobForCurrentSelection && (
            <Alert
              severity="info"
              title="Construction en cours"
              description={
                <div>
                  <div className={fr.cx('fr-mb-1w')}>
                    {activeDbJobForCurrentSelection.message ?? '...'}
                  </div>
                  <ProgressBar
                    percent={activeDbJobForCurrentSelection.percent}
                  />
                  <div className={fr.cx('fr-text--xs', 'fr-mt-1v')}>
                    {activeDbJobForCurrentSelection.percent}%
                  </div>
                </div>
              }
              className={fr.cx('fr-mt-2w')}
            />
          )}
        </section>

        {/* Existing Databases */}
        <section className={fr.cx('fr-mb-6w')}>
          <h2 className={fr.cx('fr-h3')}>Bases de données disponibles</h2>
          {databaseList && databaseList.databases.length > 0 ? (
            <Table
              headers={['Nom', 'Taille', 'Dernière modification']}
              data={databaseList.databases.map((db) => [
                db.name,
                formatFileSize(db.size_bytes),
                new Date(db.last_modified).toLocaleString('fr-FR')
              ])}
            />
          ) : (
            <p className={fr.cx('fr-text--sm')}>
              Aucune base de données disponible pour le moment. Construisez
              votre première base de données ci-dessus.
            </p>
          )}
        </section>
      </div>
    </>
  )

  // Only show tabs if user can manage databases, otherwise show build content directly
  if (authLoading) {
    return <div>Chargement...</div>
  }

  if (!canManageDatabases) {
    // User cannot manage databases - show only build tab content
    return buildDatabaseContent
  }

  // User can manage databases - show tabs
  return (
    <div className={fr.cx('fr-container', 'fr-my-6w')}>
      <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
        <div className={fr.cx('fr-col-12')}>
          <h1>Constructeur de base de données</h1>
        </div>
      </div>

      <Tabs
        tabs={[
          {
            label: 'Construire une base de données',
            content: buildDatabaseContent
          },
          {
            label: 'Gérer les bases de données',
            content: <ManageDatabases />
          }
        ]}
      />
    </div>
  )
}
