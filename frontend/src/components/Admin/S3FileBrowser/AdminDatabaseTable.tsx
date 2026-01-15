import { fr } from '@codegouvfr/react-dsfr'
import { Button } from '@codegouvfr/react-dsfr/Button'
import { Checkbox } from '@codegouvfr/react-dsfr/Checkbox'
import { Pagination } from '@codegouvfr/react-dsfr/Pagination'
import { Table } from '@codegouvfr/react-dsfr/Table'
import { useState } from 'react'
import type { SimilarityDBManifestRead } from '../../../types/api'

interface AdminDatabaseTableProps {
  databases: SimilarityDBManifestRead[]
  isLoading: boolean
  /**
   * Called when the user confirms deletion from the table.
   * ids: manifest IDs to delete (canonical identifiers)
   * labels: human-friendly labels to display in confirmation modal
   */
  onDelete: (ids: string[], labels: string[]) => void
}

/**
 * Admin-only table for managing similarity databases by manifest ID.
 *
 * This component is similar to FileListTable but works with
 * SimilarityDBManifestRead objects instead of raw S3 files. It exposes the
 * manifest UUIDs as stable identifiers and uses the S3 key as display-only
 * metadata.
 */
export const AdminDatabaseTable = ({
  databases,
  isLoading,
  onDelete
}: AdminDatabaseTableProps) => {
  const ITEMS_PER_PAGE = 50
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  if (isLoading) {
    return (
      <div className={fr.cx('fr-py-4w')}>
        <p>Chargement des bases de données...</p>
      </div>
    )
  }

  if (databases.length === 0) {
    return (
      <div className={fr.cx('fr-py-6w')} style={{ textAlign: 'center' }}>
        <p className={fr.cx('fr-text--lead')}>Aucune base de données</p>
      </div>
    )
  }

  // Pagination
  const totalPages = Math.ceil(databases.length / ITEMS_PER_PAGE)
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const endIndex = startIndex + ITEMS_PER_PAGE
  const currentItems = databases.slice(startIndex, endIndex)

  if (currentPage > totalPages && totalPages > 0) {
    setCurrentPage(1)
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

  // Selection helpers
  const handleSelect = (id: string, checked: boolean) => {
    const next = new Set(selectedIds)
    if (checked) {
      next.add(id)
    } else {
      next.delete(id)
    }
    setSelectedIds(next)
  }

  const handleSelectAllVisible = (checked: boolean) => {
    const next = new Set(selectedIds)
    currentItems.forEach((db) => {
      if (checked) {
        next.add(db.id)
      } else {
        next.delete(db.id)
      }
    })
    setSelectedIds(next)
  }

  const allVisibleSelected =
    currentItems.length > 0 &&
    currentItems.every((db) => selectedIds.has(db.id))

  const handleBatchDelete = () => {
    if (selectedIds.size === 0) return

    const ids = Array.from(selectedIds)
    const labels = databases
      .filter((db) => selectedIds.has(db.id))
      .map((db) => db.name || db.s3_key)

    onDelete(ids, labels)
    // We don't clear selection here; that happens after the modal confirms
  }

  return (
    <div className={fr.cx('fr-mt-4w')}>
      <div
        className={fr.cx('fr-mb-2w')}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <p className={fr.cx('fr-text--sm')}>
          {databases.length} base{databases.length > 1 ? 's' : ''} de données
          {totalPages > 1 && ` - Page ${currentPage} sur ${totalPages}`}
          {selectedIds.size > 0 &&
            ` - ${selectedIds.size} sélectionnée${
              selectedIds.size > 1 ? 's' : ''
            }`}
        </p>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <Button
            priority="tertiary no outline"
            size="small"
            onClick={() => handleSelectAllVisible(!allVisibleSelected)}
          >
            {allVisibleSelected
              ? 'Tout désélectionner'
              : 'Tout sélectionner (page actuelle)'}
          </Button>
          <Button
            priority="secondary"
            size="small"
            iconId="ri-delete-bin-line"
            onClick={handleBatchDelete}
            disabled={selectedIds.size === 0}
          >
            Supprimer ({selectedIds.size})
          </Button>
        </div>
      </div>

      <div
        style={{
          maxHeight: '600px',
          overflowY: 'auto'
        }}
      >
        <div className="fr-table--responsive">
          <Table
            fixed
            headers={[
              '',
              'Nom',
              'Chemin S3',
              'Taille',
              'Dernière modification'
            ]}
            data={currentItems.map((db) => [
              <div
                key={`checkbox-${db.id}`}
                style={{
                  display: 'flex',
                  justifyContent: 'flex-start',
                  flexDirection: 'row',
                  height: '20px'
                }}
              >
                <Checkbox
                  className={fr.cx('fr-mb-0')}
                  options={[
                    {
                      label: '',
                      nativeInputProps: {
                        checked: selectedIds.has(db.id),
                        onChange: (e) => handleSelect(db.id, e.target.checked)
                      }
                    }
                  ]}
                />
              </div>,
              db.name,
              db.s3_key,
              formatFileSize(db.size_bytes),
              formatDate(db.last_modified)
            ])}
          />
        </div>
      </div>

      {totalPages > 1 && (
        <div className={fr.cx('fr-mt-4w')}>
          <Pagination
            count={totalPages}
            defaultPage={currentPage}
            getPageLinkProps={(pageNumber) => ({
              onClick: (e) => {
                e.preventDefault()
                setCurrentPage(pageNumber)
                window.scrollTo({ top: 0, behavior: 'smooth' })
              },
              href: '#',
              key: `page-${pageNumber}`
            })}
          />
        </div>
      )}
    </div>
  )
}
