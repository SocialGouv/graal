import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Badge } from '@codegouvfr/react-dsfr/Badge'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { Upload } from '@codegouvfr/react-dsfr/Upload'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { useCallback, useMemo, useRef, useState } from 'react'
import { apiService } from '../../services/api'
import type { ApiError, ExcelConfigManifest } from '../../types/api'
import { ExcelConfigPermissions } from '../ExcelConfigPermissions/ExcelConfigPermissions'

type ManagedConfigSelection = {
  id: string
  fileName: string
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 octets'
  const k = 1024
  const sizes = ['octets', 'Ko', 'Mo', 'Go']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

export const ExcelConfigManager: React.FC = () => {
  const queryClient = useQueryClient()
  const [selectedConfig, setSelectedConfig] =
    useState<ManagedConfigSelection | null>(null)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const uploadRef = useRef<HTMLDivElement>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['excel-configs', 'user'],
    queryFn: () => apiService.listExcelConfigs()
  })

  const isNotFoundError = (() => {
    if (!error) return false
    const apiError = error as unknown as ApiError
    if (apiError?.status_code === 404) return true
    return (
      typeof error.message === 'string' &&
      error.message.toLowerCase().includes('not found')
    )
  })()

  const configs = data?.configs ?? []
  const showError = Boolean(error) && !isNotFoundError

  const uploadMutation = useMutation({
    mutationFn: (file: File) => apiService.uploadExcelConfig(file),
    onSuccess: (manifest) => {
      void queryClient.invalidateQueries({ queryKey: ['excel-configs'] })
      setUploadFile(null)
      setUploadError(null)
      setSuccessMessage(
        `Configuration « ${manifest.file_name} » ajoutée avec succès`
      )
      setTimeout(() => setSuccessMessage(null), 4000)
    },
    onError: (errorValue: any) => {
      setUploadError(
        errorValue?.detail || "Erreur lors de l'ajout de la configuration"
      )
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (configId: string) => apiService.deleteExcelConfig(configId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['excel-configs'] })
      setSuccessMessage('Configuration supprimée avec succès')
      setTimeout(() => setSuccessMessage(null), 4000)
    },
    onError: (errorValue: any) => {
      setUploadError(
        errorValue?.detail ||
          'Erreur lors de la suppression de la configuration'
      )
    }
  })

  const handleUpload = () => {
    if (!uploadFile) {
      setUploadError('Veuillez sélectionner un fichier .xlsx')
      return
    }

    if (!uploadFile.name.toLowerCase().endsWith('.xlsx')) {
      setUploadError('Seuls les fichiers .xlsx sont acceptés')
      return
    }

    setUploadError(null)
    uploadMutation.mutate(uploadFile)
  }

  const handleFileSelection = useCallback((file: File | null) => {
    setUploadFile(file)
    setUploadError(null)
  }, [])

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      event.stopPropagation()
      setIsDragOver(false)
      const file = event.dataTransfer.files?.[0] ?? null
      if (!file) {
        return
      }
      if (!file.name.toLowerCase().endsWith('.xlsx')) {
        setUploadFile(null)
        setUploadError('Seuls les fichiers .xlsx sont acceptés')
        return
      }
      handleFileSelection(file)
    },
    [handleFileSelection]
  )

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragOver(false)
  }, [])

  const handleClickUpload = useCallback(() => {
    if (uploadMutation.isPending) return
    const fileInput = uploadRef.current?.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement | null
    fileInput?.click()
  }, [uploadMutation.isPending])

  const renderRoleBadge = useCallback(
    (role: ExcelConfigManifest['current_user_role']) => {
      if (role === 'owner') {
        return (
          <Badge severity="success" noIcon small>
            Propriétaire
          </Badge>
        )
      }
      return (
        <Badge severity="info" noIcon small>
          Lecteur
        </Badge>
      )
    },
    []
  )
  const canManageConfig = useCallback(
    (config: ExcelConfigManifest) => config.current_user_role === 'owner',
    []
  )
  const tableRows = useMemo(
    () =>
      configs.map((config) => [
        config.file_name,
        renderRoleBadge(config.current_user_role),
        formatBytes(config.file_size_bytes),
        new Date(config.created_at).toLocaleDateString('fr-FR'),
        <div
          key={config.id}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}
        >
          {canManageConfig(config) && (
            <Button
              priority="secondary"
              size="small"
              onClick={() =>
                setSelectedConfig({
                  id: config.id,
                  fileName: config.file_name
                })
              }
            >
              Gérer les permissions
            </Button>
          )}
          {canManageConfig(config) && (
            <Button
              priority="tertiary no outline"
              size="small"
              iconId="fr-icon-delete-line"
              title="Supprimer"
              nativeButtonProps={{
                'aria-label': 'Supprimer'
              }}
              onClick={() => {
                if (
                  window.confirm(
                    `Supprimer la configuration « ${config.file_name} » ?`
                  )
                ) {
                  deleteMutation.mutate(config.id)
                }
              }}
            >
              <span className={fr.cx('fr-sr-only')}>Supprimer</span>
            </Button>
          )}
        </div>
      ]),
    [configs, deleteMutation, renderRoleBadge, canManageConfig]
  )

  if (selectedConfig) {
    return (
      <ExcelConfigPermissions
        configId={selectedConfig.id}
        configName={selectedConfig.fileName}
        onClose={() => setSelectedConfig(null)}
      />
    )
  }

  return (
    <div>
      <h2>Gérer les configurations Excel</h2>
      <p className={fr.cx('fr-mb-4w')}>
        Importez vos fichiers de configuration Excel et partagez-les avec vos
        collaborateurs.
      </p>

      {successMessage && (
        <Alert
          severity="success"
          title="Succès"
          description={successMessage}
          className={fr.cx('fr-mb-3w')}
        />
      )}

      <section className={fr.cx('fr-mb-6w')}>
        <h3 className={fr.cx('fr-h6', 'fr-mb-2w')}>
          Ajouter une configuration
        </h3>
        <button
          type="button"
          className={fr.cx('fr-upload-group', 'fr-p-4w', 'fr-mb-2w')}
          style={{
            border: '2px dashed var(--border-default-grey)',
            borderRadius: '0.5rem',
            textAlign: 'center',
            cursor: uploadMutation.isPending ? 'not-allowed' : 'pointer',
            backgroundColor: isDragOver
              ? 'var(--background-contrast-blue-france)'
              : 'var(--background-default-grey)',
            opacity: uploadMutation.isPending ? 0.6 : 1
          }}
          onClick={handleClickUpload}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className={fr.cx('fr-text--lg', 'fr-mb-1w')}>
            Glissez-déposez votre fichier Excel ici
          </div>
          <div className={fr.cx('fr-text--sm', 'fr-mb-2w')}>
            ou cliquez pour sélectionner un fichier .xlsx
          </div>
          {uploadFile ? (
            <Badge severity="success" noIcon>
              {uploadFile.name}
            </Badge>
          ) : (
            <Badge severity="info" noIcon>
              Aucun fichier sélectionné
            </Badge>
          )}
        </button>

        <div ref={uploadRef} className={fr.cx('fr-sr-only')}>
          <Upload
            label="Fichier Excel (.xlsx)"
            hint="Sélectionnez un fichier Excel contenant les correspondances d'acronymes"
            state={uploadError ? 'error' : 'default'}
            stateRelatedMessage={uploadError ?? undefined}
            disabled={uploadMutation.isPending}
            nativeInputProps={{
              accept: '.xlsx',
              onChange: (event) => {
                const file = event.target.files?.[0] ?? null
                handleFileSelection(file)
              }
            }}
          />
        </div>
        {uploadFile && (
          <p className={fr.cx('fr-text--sm', 'fr-mt-1w')}>
            <strong>Fichier sélectionné :</strong> {uploadFile.name}
          </p>
        )}
        <div className={fr.cx('fr-mt-2w')}>
          <Button
            onClick={handleUpload}
            disabled={!uploadFile || uploadMutation.isPending}
            iconId="fr-icon-upload-line"
          >
            {uploadMutation.isPending ? 'Téléversement...' : 'Ajouter'}
          </Button>
        </div>
      </section>

      {showError && error && (
        <Alert
          severity="error"
          title="Erreur"
          description={error.message || 'Erreur lors du chargement'}
          className={fr.cx('fr-mb-3w')}
        />
      )}

      {isLoading ? (
        <p>Chargement des configurations...</p>
      ) : configs.length > 0 ? (
        <Table
          headers={['Nom', 'Rôle', 'Taille', 'Ajouté le', 'Actions']}
          data={tableRows}
        />
      ) : (
        <p className={fr.cx('fr-text--sm')}>
          Aucun fichier de configuration n'a été ajouté.
        </p>
      )}
    </div>
  )
}
