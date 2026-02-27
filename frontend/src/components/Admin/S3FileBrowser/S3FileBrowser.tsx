import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Tabs } from '@codegouvfr/react-dsfr/Tabs'
import { useState } from 'react'
import {
  useAdminDatabases,
  useDeleteAdminDatabase
} from '../../../hooks/useAdminDatabases'
import {
  useAdminExcelConfigs,
  useDeleteAdminExcelConfig,
  useDeleteInputPoolFile,
  useInputPoolFiles
} from '../../../hooks/useS3Files'
import { AdminLlmConfigs } from '../LlmConfigs/AdminLlmConfigs'
import { AdminDatabaseTable } from './AdminDatabaseTable'
import { DeleteConfirmModal, deleteConfirmModal } from './DeleteConfirmModal'
import { FileListTable } from './FileListTable'

export const S3FileBrowser = () => {
  // State for delete modal
  const [deleteTarget, setDeleteTarget] = useState<{
    // S3 keys (or identifiers) used for deletion
    keys: string[]
    // Human-readable labels displayed in the confirmation modal
    labels: string[]
    // Optional internal IDs (used for database manifests)
    ids?: string[]
    type: 'config' | 'database' | 'input'
  } | null>(null)

  // Query hooks
  const {
    data: configData,
    isLoading: configLoading,
    error: configError
  } = useAdminExcelConfigs()
  const {
    data: databaseData,
    isLoading: databaseLoading,
    error: databaseError
  } = useAdminDatabases()
  const {
    data: inputData,
    isLoading: inputLoading,
    error: inputError
  } = useInputPoolFiles()

  // Mutation hooks
  const deleteConfigMutation = useDeleteAdminExcelConfig()
  const deleteAdminDatabaseMutation = useDeleteAdminDatabase()
  const deleteInputMutation = useDeleteInputPoolFile()

  // Handle delete confirmation (batch deletion)
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return

    try {
      // Delete all selected files sequentially
      for (const key of deleteTarget.keys) {
        if (deleteTarget.type === 'config') {
          await deleteConfigMutation.mutateAsync(key)
        } else if (deleteTarget.type === 'database') {
          // For databases we delete by manifest ID, not by S3 key. Fallback
          // to using the label as ID if ids are missing for any reason.
          const ids = deleteTarget.ids ?? deleteTarget.keys
          const index = deleteTarget.keys.indexOf(key)
          const id = ids[index] ?? key
          await deleteAdminDatabaseMutation.mutateAsync(id)
        } else if (deleteTarget.type === 'input') {
          await deleteInputMutation.mutateAsync(key)
        }
      }

      // Close modal on success
      deleteConfirmModal.close()
      setDeleteTarget(null)
    } catch (error) {
      // Error is handled by React Query
      console.error('Delete failed:', error)
      // Don't close modal on error so user can see the error message
    }
  }

  // Handle delete button click (supports batch deletion)
  const handleDelete = (
    keys: string[],
    type: 'config' | 'database' | 'input',
    ids?: string[]
  ) => {
    const labels =
      type === 'config'
        ? keys.map(
            (key) =>
              excelConfigs.find((config) => config.id === key)?.file_name || key
          )
        : keys
    setDeleteTarget({ keys, labels, type, ids })
    deleteConfirmModal.open()
  }

  const handleInputDelete = (fileKeys: string[]) => {
    // Convert keys to user-friendly labels when possible.
    const labelByKey = new Map(
      (inputData?.files ?? []).map((f) => [f.key, f.display_name || f.key])
    )
    const labels = fileKeys.map((k) => labelByKey.get(k) || k)
    setDeleteTarget({ keys: fileKeys, labels, type: 'input' })
    deleteConfirmModal.open()
  }

  // Handle modal cancel
  const handleDeleteCancel = () => {
    deleteConfirmModal.close()
    setDeleteTarget(null)
  }

  const isDeleting =
    deleteConfigMutation.isPending ||
    deleteAdminDatabaseMutation.isPending ||
    deleteInputMutation.isPending

  const excelConfigs = configData?.configs ?? []

  return (
    <div>
      <h2 className={fr.cx('fr-h4', 'fr-mb-3w')}>Gestion des fichiers</h2>

      {/* Display errors */}
      {configError && (
        <Alert
          severity="error"
          title="Erreur de chargement"
          description="Impossible de charger les configurations Excel"
          className={fr.cx('fr-mb-4w')}
        />
      )}
      {databaseError && (
        <Alert
          severity="error"
          title="Erreur de chargement"
          description="Impossible de charger les bases de données"
          className={fr.cx('fr-mb-4w')}
        />
      )}
      {inputError && (
        <Alert
          severity="error"
          title="Erreur de chargement"
          description="Impossible de charger les fichiers du pool d'entrée"
          className={fr.cx('fr-mb-4w')}
        />
      )}

      {/* Display delete errors */}
      {deleteConfigMutation.isError && (
        <Alert
          severity="error"
          title="Erreur de suppression"
          description={
            deleteConfigMutation.error?.message ||
            'Impossible de supprimer la configuration Excel'
          }
          className={fr.cx('fr-mb-4w')}
        />
      )}
      {deleteAdminDatabaseMutation.isError && (
        <Alert
          severity="error"
          title="Erreur de suppression"
          description={
            deleteAdminDatabaseMutation.error?.message ||
            'Impossible de supprimer la base de données'
          }
          className={fr.cx('fr-mb-4w')}
        />
      )}
      {deleteInputMutation.isError && (
        <Alert
          severity="error"
          title="Erreur de suppression"
          description={
            (deleteInputMutation.error as Error)?.message ||
            "Impossible de supprimer le fichier du pool d'entrée"
          }
          className={fr.cx('fr-mb-4w')}
        />
      )}

      <Tabs
        tabs={[
          {
            label: 'Configurations LLM',
            content: <AdminLlmConfigs />
          },
          {
            label: 'Configurations Excel',
            content: (
              <FileListTable
                files={excelConfigs.map((config) => ({
                  key: config.id,
                  size: config.file_size_bytes,
                  last_modified: config.updated_at,
                  file_type: 'config',
                  display_name: config.file_name
                }))}
                isLoading={configLoading}
                onDelete={(fileKeys) => handleDelete(fileKeys, 'config')}
                fileType="config"
              />
            )
          },
          {
            label: 'Bases de données',
            content: (
              <AdminDatabaseTable
                databases={databaseData || []}
                isLoading={databaseLoading}
                onDelete={(ids: string[], labels: string[]) =>
                  handleDelete(labels, 'database', ids)
                }
              />
            )
          },
          {
            label: "Pool d'entrée",
            content: (
              <FileListTable
                files={inputData?.files || []}
                isLoading={inputLoading}
                onDelete={handleInputDelete}
                fileType="input"
              />
            )
          }
        ]}
      />

      {/* Delete confirmation modal */}
      <DeleteConfirmModal
        isOpen={deleteTarget !== null}
        labels={deleteTarget?.labels || []}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        isDeleting={isDeleting}
      />
    </div>
  )
}
