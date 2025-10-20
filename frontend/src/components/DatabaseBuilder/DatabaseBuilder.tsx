import React, { useState } from 'react'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Upload } from '@codegouvfr/react-dsfr/Upload'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Badge } from '@codegouvfr/react-dsfr/Badge'
import { fr } from '@codegouvfr/react-dsfr'
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiService } from '../../services/api'
import { useProcessingStore } from '../../stores/processingStore'
import { ConfigFileSelector } from '../ConfigFileSelector'
import type { FileReference } from '../../types/api'

interface PendingFile {
  file: File
  timestamp: string
  originProject: string
  id: string
  dateAutoExtracted?: boolean
}

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
  const {
    databaseBuilder,
    setDatabaseConfigFile,
    setDatabaseName,
    addUploadedFile,
    removeUploadedFile,
    setJobId
  } = useProcessingStore()

  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [buildError, setBuildError] = useState<string | null>(null)

  // Query for listing databases
  const { data: databaseList, refetch: refetchDatabases } = useQuery({
    queryKey: ['databases'],
    queryFn: () => apiService.listDatabases(),
    refetchInterval: false
  })

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
        config_file: databaseBuilder.selectedConfigFile!,
        database_name: databaseBuilder.databaseName,
        file_references: fileReferences
      })
    },
    onSuccess: (data) => {
      setJobId(data.job_id)
      setBuildError(null)
      // Refetch database list after build completes (with delay)
      setTimeout(() => {
        void refetchDatabases()
      }, 2000)
    },
    onError: (error: any) => {
      setBuildError(error.detail || error.message || 'Failed to build database')
    }
  })

  // Mutation for deleting uploaded file
  const deleteMutation = useMutation({
    mutationFn: (uploadId: string) => apiService.deleteUploadedFile(uploadId),
    onSuccess: (_data, uploadId) => {
      removeUploadedFile(uploadId)
    }
  })

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
    if (
      !databaseBuilder.selectedConfigFile ||
      !databaseBuilder.databaseName ||
      databaseBuilder.uploadedFiles.length === 0
    ) {
      setBuildError(
        'Veuillez sélectionner un fichier de configuration, fournir un nom de base de données et télécharger au moins un fichier'
      )
      return
    }

    // Validate that all uploaded files have timestamps (either manual or auto-extracted)
    const filesWithoutTimestamp = databaseBuilder.uploadedFiles.filter(
      (file) => !file.timestamp
    )

    if (filesWithoutTimestamp.length > 0) {
      setBuildError(
        `${filesWithoutTimestamp.length} fichier(s) n'ont pas d'horodatage. Veuillez fournir un horodatage pour tous les fichiers avant de construire la base de données.`
      )
      return
    }

    const fileReferences: FileReference[] = databaseBuilder.uploadedFiles.map(
      (file) => ({
        upload_id: file.uploadId,
        filename: file.filename,
        default_processing_timestamp: file.timestamp,
        origin_project: file.originProject
      })
    )

    buildMutation.mutate(fileReferences)
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  return (
    <div className={fr.cx('fr-container', 'fr-my-6w')}>
      <div className={fr.cx('fr-grid-row', 'fr-grid-row--gutters')}>
        <div className={fr.cx('fr-col-12')}>
          <h1>Constructeur de base de données</h1>
          <p className={fr.cx('fr-text--lead')}>
            Créez des bases de données de similarité à partir de fichiers
            d'amendements pour la recherche de similarité.
          </p>
        </div>
      </div>

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

      {/* Step 2: Database Name */}
      <section className={fr.cx('fr-mb-6w', 'fr-mt-4w')}>
        <h2 className={fr.cx('fr-h3')}>2. Nommer votre base de données</h2>
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
            Vous devez sélectionner un fichier de configuration pour continuer
          </p>
        )}
      </section>

      {/* Step 3: Upload Files */}
      <section className={fr.cx('fr-mb-6w')}>
        <h2 className={fr.cx('fr-h3')}>
          3. Télécharger les fichiers d'amendements
        </h2>

        <div className={fr.cx('fr-mb-3w')}>
          <Upload
            label="Sélectionner des fichiers d'amendements"
            hint="Sélectionnez un ou plusieurs fichiers JSON ou Excel (.json, .xlsx, .xls)"
            nativeInputProps={{
              onChange: async (e) => {
                const files = e.target.files
                if (files && files.length > 0) {
                  setUploadError(null)

                  // Process files and extract dates for JSON files
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
                        const fileContent = await new Promise<string>(
                          (resolve, reject) => {
                            const reader = new FileReader()
                            reader.onload = (event) =>
                              resolve(event.target?.result as string)
                            reader.onerror = (error) => reject(error)
                            reader.readAsText(file)
                          }
                        )

                        const extractedDate =
                          extractDateFromAmendmentJSON(fileContent)
                        if (extractedDate) {
                          pendingFile.timestamp = extractedDate
                          pendingFile.dateAutoExtracted = true
                        }
                      } catch (error) {
                        console.error(
                          `Failed to read file ${file.name}:`,
                          error
                        )
                      }
                    }

                    return pendingFile
                  })

                  const newPendingFiles = await Promise.all(filePromises)
                  setPendingFiles((prev) => [...prev, ...newPendingFiles])

                  // Reset the input to allow re-selecting the same files
                  e.target.value = ''
                }
              },
              accept: '.json,.xlsx,.xls',
              multiple: true,
              disabled:
                !databaseBuilder.selectedConfigFile ||
                !databaseBuilder.databaseName
            }}
          />
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
            !databaseBuilder.selectedConfigFile ||
            !databaseBuilder.databaseName ||
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
        {(!databaseBuilder.selectedConfigFile ||
          !databaseBuilder.databaseName) && (
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
                  {new Date(file.timestamp * 1000).toLocaleDateString('fr-FR')}
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
        <h2 className={fr.cx('fr-h3')}>4. Construire la base de données</h2>
        <p>
          Cela traitera tous les fichiers téléchargés et créera une base de
          données de similarité qui pourra être utilisée pour les opérations de
          recherche de similarité.
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
            !databaseBuilder.selectedConfigFile ||
            !databaseBuilder.databaseName ||
            databaseBuilder.uploadedFiles.length === 0 ||
            buildMutation.isPending
          }
          iconId="fr-icon-checkbox-circle-line"
          iconPosition="left"
          className="fr-btn--block"
        >
          {buildMutation.isPending
            ? 'Construction...'
            : 'Construire la base de données'}
        </Button>
        {(!databaseBuilder.selectedConfigFile ||
          !databaseBuilder.databaseName ||
          databaseBuilder.uploadedFiles.length === 0) && (
          <p className={fr.cx('fr-text--sm', 'fr-hint-text', 'fr-mt-2w')}>
            Veuillez compléter toutes les étapes précédentes avant de construire
            la base de données
          </p>
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
            Aucune base de données disponible pour le moment. Construisez votre
            première base de données ci-dessus.
          </p>
        )}
      </section>
    </div>
  )
}
