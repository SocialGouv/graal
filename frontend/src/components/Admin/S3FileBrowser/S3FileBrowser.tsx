import { fr } from '@codegouvfr/react-dsfr'
import { Alert } from '@codegouvfr/react-dsfr/Alert'
import { Tabs } from '@codegouvfr/react-dsfr/Tabs'
import { useState } from 'react'
import {
  useConfigFiles,
  useDatabaseFiles,
  useDeleteConfigFile,
  useDeleteDatabaseFile,
  useDeleteInputPoolFile,
  useInputPoolFiles
} from '../../../hooks/useS3Files'
import { DeleteConfirmModal, deleteConfirmModal } from './DeleteConfirmModal'
import { FileListTable } from './FileListTable'

export const S3FileBrowser = () => {
  // State for delete modal
  const [deleteTarget, setDeleteTarget] = useState<{
    fileNames: string[]
    type: 'config' | 'database' | 'input'
  } | null>(null)

  // Query hooks
  const {
    data: configData,
    isLoading: configLoading,
    error: configError
  } = useConfigFiles()
  const {
    data: databaseData,
    isLoading: databaseLoading,
    error: databaseError
  } = useDatabaseFiles()
  const {
    data: inputData,
    isLoading: inputLoading,
    error: inputError
  } = useInputPoolFiles()

  // Mutation hooks
  const deleteConfigMutation = useDeleteConfigFile()
  const deleteDatabaseMutation = useDeleteDatabaseFile()
  const deleteInputMutation = useDeleteInputPoolFile()

  // Handle delete confirmation (batch deletion)
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return

    try {
      // Delete all selected files sequentially
      for (const fileName of deleteTarget.fileNames) {
        if (deleteTarget.type === 'config') {
          await deleteConfigMutation.mutateAsync(fileName)
        } else if (deleteTarget.type === 'database') {
          await deleteDatabaseMutation.mutateAsync(fileName)
        } else if (deleteTarget.type === 'input') {
          await deleteInputMutation.mutateAsync(fileName)
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
    fileNames: string[],
    type: 'config' | 'database' | 'input'
  ) => {
    setDeleteTarget({ fileNames, type })
    deleteConfirmModal.open()
  }

  // Handle modal cancel
  const handleDeleteCancel = () => {
    deleteConfirmModal.close()
    setDeleteTarget(null)
  }

  const isDeleting =
    deleteConfigMutation.isPending ||
    deleteDatabaseMutation.isPending ||
    deleteInputMutation.isPending

  return (
    <div>
      <h2 className={fr.cx('fr-h4', 'fr-mb-3w')}>Gestion des fichiers S3</h2>

      {/* Display errors */}
      {configError && (
        <Alert
          severity="error"
          title="Erreur de chargement"
          description="Impossible de charger les fichiers de configuration"
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
            (deleteConfigMutation.error as Error)?.message ||
            'Impossible de supprimer le fichier de configuration'
          }
          className={fr.cx('fr-mb-4w')}
        />
      )}
      {deleteDatabaseMutation.isError && (
        <Alert
          severity="error"
          title="Erreur de suppression"
          description={
            (deleteDatabaseMutation.error as Error)?.message ||
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
            label: 'Fichiers de configuration',
            content: (
              <FileListTable
                files={configData?.files || []}
                isLoading={configLoading}
                onDelete={(fileNames) => handleDelete(fileNames, 'config')}
                fileType="config"
              />
            )
          },
          {
            label: 'Bases de données',
            content: (
              <FileListTable
                files={databaseData?.files || []}
                isLoading={databaseLoading}
                onDelete={(fileNames) => handleDelete(fileNames, 'database')}
                fileType="database"
              />
            )
          },
          {
            label: "Pool d'entrée",
            content: (
              <FileListTable
                files={inputData?.files || []}
                isLoading={inputLoading}
                onDelete={(fileNames) => handleDelete(fileNames, 'input')}
                fileType="input"
              />
            )
          }
        ]}
      />

      {/* Delete confirmation modal */}
      <DeleteConfirmModal
        isOpen={deleteTarget !== null}
        fileNames={deleteTarget?.fileNames || []}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        isDeleting={isDeleting}
      />
    </div>
  )
}
