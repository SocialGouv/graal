import { createModal } from '@codegouvfr/react-dsfr/Modal'

const deleteModal = createModal({
  id: 'user-config-delete-confirm-modal',
  isOpenedByDefault: false
})

export const userConfigDeleteConfirmModal = deleteModal

interface UserConfigDeleteConfirmModalProps {
  configName: string
  onConfirm: () => void
  onCancel: () => void
  isDeleting: boolean
}

export const UserConfigDeleteConfirmModal = ({
  configName,
  onConfirm,
  onCancel,
  isDeleting
}: UserConfigDeleteConfirmModalProps) => {
  return (
    <deleteModal.Component
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
          priority: 'primary',
          onClick: onConfirm,
          disabled: isDeleting
        }
      ]}
    >
      <p>
        Êtes-vous sûr de vouloir supprimer la configuration{' '}
        <strong>{configName}</strong> ?
      </p>
      <p style={{ color: 'var(--text-default-warning)' }}>
        ⚠️ Cette action est irréversible.
      </p>
    </deleteModal.Component>
  )
}

const unsavedModal = createModal({
  id: 'user-config-unsaved-changes-modal',
  isOpenedByDefault: false
})

export const userConfigUnsavedChangesModal = unsavedModal

interface UserConfigUnsavedChangesModalProps {
  onConfirmLoseChanges: () => void
  onCancel: () => void
}

export const UserConfigUnsavedChangesModal = ({
  onConfirmLoseChanges,
  onCancel
}: UserConfigUnsavedChangesModalProps) => {
  return (
    <unsavedModal.Component
      title="Modifications non sauvegardées"
      buttons={[
        {
          children: 'Annuler',
          priority: 'secondary',
          onClick: onCancel
        },
        {
          children: 'Continuer sans sauvegarder',
          priority: 'primary',
          onClick: onConfirmLoseChanges
        }
      ]}
    >
      <p>
        Vous avez des modifications non sauvegardées. Si vous continuez, elles
        seront perdues.
      </p>
    </unsavedModal.Component>
  )
}
