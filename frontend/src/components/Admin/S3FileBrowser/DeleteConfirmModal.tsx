import { createModal } from '@codegouvfr/react-dsfr/Modal'

interface DeleteConfirmModalProps {
  isOpen: boolean
  fileNames: string[]
  onConfirm: () => void
  onCancel: () => void
  isDeleting: boolean
}

const modal = createModal({
  id: 's3-delete-confirm-modal',
  isOpenedByDefault: false
})

export const DeleteConfirmModal = ({
  isOpen: _isOpen,
  fileNames,
  onConfirm,
  onCancel,
  isDeleting
}: DeleteConfirmModalProps) => {
  const fileCount = fileNames.length
  const isMultiple = fileCount > 1

  return (
    <modal.Component
      title="Confirmer la suppression"
      buttons={[
        {
          children: 'Annuler',
          priority: 'secondary',
          onClick: onCancel,
          disabled: isDeleting
        },
        {
          children: isDeleting ? 'Suppression...' : 'Supprimer',
          onClick: onConfirm,
          disabled: isDeleting,
          priority: 'primary'
        }
      ]}
    >
      {isMultiple ? (
        <>
          <p>
            Êtes-vous sûr de vouloir supprimer{' '}
            <strong>{fileCount} fichiers</strong> ?
          </p>
          <ul style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {fileNames.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </>
      ) : (
        <p>
          Êtes-vous sûr de vouloir supprimer le fichier{' '}
          <strong>{fileNames[0]}</strong> ?
        </p>
      )}
      <p style={{ color: 'var(--text-default-warning)' }}>
        ⚠️ Cette action est irréversible et{' '}
        {isMultiple
          ? 'les fichiers seront définitivement supprimés'
          : 'le fichier sera définitivement supprimé'}{' '}
        de S3.
      </p>
    </modal.Component>
  )
}

// Export the modal control for external use
export const deleteConfirmModal = modal
