import { createModal } from '@codegouvfr/react-dsfr/Modal'

import type { S3FileMetadata } from '../../../types/api'

const modal = createModal({
  id: 'input-pool-file-details-modal',
  isOpenedByDefault: false
})

export const inputPoolFileDetailsModal = modal

interface InputPoolFileDetailsModalProps {
  file: S3FileMetadata | null
  onClose: () => void
}

const formatFileSize = (bytes: number): string => {
  if (!Number.isFinite(bytes) || bytes <= 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

const formatDate = (isoString: string): string => {
  if (!isoString) return '—'
  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

export const InputPoolFileDetailsModal = ({
  file,
  onClose
}: InputPoolFileDetailsModalProps) => {
  const displayName = file?.display_name || file?.key || '—'

  return (
    <modal.Component
      title="Détails du fichier (pool d'entrée)"
      buttons={[
        {
          children: 'Fermer',
          priority: 'primary',
          onClick: onClose
        }
      ]}
    >
      {!file ? (
        <p>—</p>
      ) : (
        <div>
          <p>
            <strong>Nom affiché :</strong> {displayName}
          </p>

          <p>
            <strong>Clé S3 :</strong> {file.key}
          </p>

          <p>
            <strong>Hash :</strong> {file.file_hash || '—'}
          </p>

          <p>
            <strong>Taille :</strong> {formatFileSize(file.size)}
          </p>

          <p>
            <strong>Dernière modification :</strong>{' '}
            {formatDate(file.last_modified)}
          </p>

          {file.known_filenames && file.known_filenames.length > 0 && (
            <>
              <p>
                <strong>Nom(s) connu(s) :</strong>
              </p>
              <ul>
                {file.known_filenames.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            </>
          )}

          {file.referenced_by_databases &&
            file.referenced_by_databases.length > 0 && (
              <>
                <p>
                  <strong>Référencé par les bases :</strong>
                </p>
                <ul>
                  {file.referenced_by_databases.map((db) => (
                    <li key={db.id}>
                      {db.name} ({db.id})
                    </li>
                  ))}
                </ul>
              </>
            )}
        </div>
      )}
    </modal.Component>
  )
}
