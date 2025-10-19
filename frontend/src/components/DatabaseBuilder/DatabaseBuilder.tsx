import React, { useState } from 'react'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Input } from '@codegouvfr/react-dsfr/Input'
import { Upload } from '@codegouvfr/react-dsfr/Upload'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { fr } from '@codegouvfr/react-dsfr'
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiService } from '../../services/api'
import { useProcessingStore } from '../../stores/processingStore'
import { ConfigFileSelector } from '../ConfigFileSelector'
import type { FileReference } from '../../types/api'

export const DatabaseBuilder: React.FC = () => {
  const {
    databaseBuilder,
    setDatabaseConfigFile,
    setDatabaseName,
    addUploadedFile,
    removeUploadedFile,
    setJobId
  } = useProcessingStore()

  const [currentFile, setCurrentFile] = useState<File | null>(null)
  const [timestamp, setTimestamp] = useState<string>('')
  const [originProject, setOriginProject] = useState<string>('')
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
      metadata: { default_processing_timestamp: number; origin_project: string }
    }) => apiService.uploadAmendmentFile(params.file, params.metadata),
    onSuccess: (data, variables) => {
      addUploadedFile({
        uploadId: data.upload_id,
        filename: data.filename,
        size: data.size,
        timestamp: variables.metadata.default_processing_timestamp,
        originProject: variables.metadata.origin_project
      })
      // Reset form
      setCurrentFile(null)
      setTimestamp('')
      setOriginProject('')
      setUploadError(null)
    },
    onError: (error: Error) => {
      setUploadError(error.message || 'Failed to upload file')
    }
  })

  // Mutation for building database
  const buildMutation = useMutation({
    mutationFn: (fileReferences: FileReference[]) =>
      apiService.buildDatabase({
        config_file: databaseBuilder.selectedConfigFile!,
        database_name: databaseBuilder.databaseName,
        file_references: fileReferences
      }),
    onSuccess: (data) => {
      setJobId(data.job_id)
      setBuildError(null)
      // Refetch database list after build completes (with delay)
      setTimeout(() => {
        void refetchDatabases()
      }, 2000)
    },
    onError: (error: Error) => {
      setBuildError(error.message || 'Failed to build database')
    }
  })

  // Mutation for deleting uploaded file
  const deleteMutation = useMutation({
    mutationFn: (uploadId: string) => apiService.deleteUploadedFile(uploadId),
    onSuccess: (_data, uploadId) => {
      removeUploadedFile(uploadId)
    }
  })

  const handleFileUpload = () => {
    if (!currentFile || !timestamp || !originProject) {
      setUploadError('Please fill in all fields')
      return
    }

    const timestampSeconds = new Date(timestamp).getTime() / 1000

    uploadMutation.mutate({
      file: currentFile,
      metadata: {
        default_processing_timestamp: timestampSeconds,
        origin_project: originProject
      }
    })
  }

  const handleBuildDatabase = () => {
    if (
      !databaseBuilder.selectedConfigFile ||
      !databaseBuilder.databaseName ||
      databaseBuilder.uploadedFiles.length === 0
    ) {
      setBuildError(
        'Please select a config file, provide a database name and upload at least one file'
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
            label="Sélectionner un fichier d'amendement"
            hint="Fichiers JSON ou Excel (.json, .xlsx, .xls)"
            nativeInputProps={{
              onChange: (e) => {
                const file = e.target.files?.[0]
                if (file) {
                  setCurrentFile(file)
                  setUploadError(null)
                }
              },
              accept: '.json,.xlsx,.xls',
              disabled:
                !databaseBuilder.selectedConfigFile ||
                !databaseBuilder.databaseName
            }}
          />
          {currentFile && (
            <p className={fr.cx('fr-text--sm', 'fr-mt-1w')}>
              Sélectionné : {currentFile.name} (
              {formatFileSize(currentFile.size)})
            </p>
          )}
        </div>

        <Input
          label="Horodatage de traitement"
          hintText="Date et heure du traitement des amendements"
          nativeInputProps={{
            type: 'datetime-local',
            value: timestamp,
            onChange: (e) => {
              setTimestamp(e.target.value)
              setUploadError(null)
            },
            disabled:
              !databaseBuilder.selectedConfigFile ||
              !databaseBuilder.databaseName
          }}
          className={fr.cx('fr-mb-2w')}
        />

        <Input
          label="Projet d'origine"
          hintText="Nom du projet législatif (ex: PLFSS 2024)"
          nativeInputProps={{
            value: originProject,
            onChange: (e) => {
              setOriginProject(e.target.value)
              setUploadError(null)
            },
            placeholder: 'ex: PLFSS 2024',
            disabled:
              !databaseBuilder.selectedConfigFile ||
              !databaseBuilder.databaseName
          }}
          className={fr.cx('fr-mb-3w')}
        />

        {uploadError && (
          <Alert
            severity="error"
            title="Erreur de téléchargement"
            description={uploadError}
            className={fr.cx('fr-mb-3w')}
          />
        )}

        <Button
          onClick={handleFileUpload}
          disabled={
            !databaseBuilder.selectedConfigFile ||
            !databaseBuilder.databaseName ||
            !currentFile ||
            !timestamp ||
            !originProject ||
            uploadMutation.isPending
          }
          iconId="fr-icon-upload-line"
          iconPosition="left"
        >
          {uploadMutation.isPending
            ? 'Téléchargement...'
            : 'Ajouter le fichier'}
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
                new Date(file.timestamp * 1000).toLocaleString('fr-FR'),
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
